"""Dynamic LangGraph Builder for Domain Pack Multi-Agent Workflows."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict

from app.llm.base import LLMProvider, extract_json_from_text
from app.memory import SessionMemoryStore
from app.schemas import DomainPack, StepTrace, ToolCallRecord
from app.tools.base import ToolContext
from app.tools.registry import ToolRegistry
from langgraph.graph import END, StateGraph
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("orchestrator-graph")


class AgentGraphState(TypedDict):
    """Shared typed state propagated across LangGraph nodes."""

    run_id: str
    session_id: str
    pack_name: str
    input_data: Dict[str, Any]
    agent_outputs: Dict[str, Any]
    current_agent: str
    next_agent: Optional[str]
    confidence: float
    status: str  # "running", "awaiting_approval", "completed", "rejected", "failed"
    escalation_reason: Optional[str]
    pending_approval: bool
    trace_steps: List[Dict[str, Any]]
    final_output: Optional[Dict[str, Any]]


def safe_evaluate_condition(condition_str: str, eval_context: Dict[str, Any]) -> bool:
    """Safely evaluate boolean condition expressions against execution state context."""
    if not condition_str or condition_str.strip().lower() == "true":
        return True

    try:
        # Evaluate simple python expressions using restricted builtins
        return bool(eval(condition_str, {"__builtins__": {}}, eval_context))
    except Exception as exc:
        logger.debug("Condition eval error for '%s': %s", condition_str, exc)
        return False


class DynamicGraphBuilder:
    """Compiles a declarative DomainPack specification into an executable LangGraph StateGraph."""

    def __init__(
        self,
        pack: DomainPack,
        tool_registry: ToolRegistry,
        llm_provider: LLMProvider,
        memory_store: SessionMemoryStore,
        verifier_url: str = "http://localhost:8001",
    ) -> None:
        self.pack = pack
        self.tool_registry = tool_registry
        self.llm_provider = llm_provider
        self.memory_store = memory_store
        self.verifier_url = verifier_url

    def build(self, checkpointer=None) -> Any:
        """Construct, wire nodes and conditional edges, and compile the state graph."""
        builder = StateGraph(AgentGraphState)

        # 1. Add an agent node for each agent defined in the pack
        for agent_def in self.pack.agents:
            node_func = self._create_agent_node(agent_def)
            builder.add_node(agent_def.name, node_func)

        # 2. Set the designated entry agent
        builder.set_entry_point(self.pack.entry_agent)

        # 3. Add conditional routing edges
        for agent_def in self.pack.agents:
            source_agent = agent_def.name
            rules_for_agent = [
                r for r in self.pack.routing_rules if r.from_agent == source_agent
            ]

            # Collect all possible destination targets for path map
            targets = {r.to_agent for r in rules_for_agent}
            path_map = {}
            for target in targets:
                if target == "END":
                    path_map["END"] = END
                else:
                    path_map[target] = target
            path_map["__end__"] = END

            def make_router(agent_rules):
                def route_next(state: AgentGraphState) -> str:
                    # If paused for human review, terminate current execution run
                    if state.get("pending_approval") or state.get("status") == "awaiting_approval":
                        return "__end__"
                    if state.get("status") in ("completed", "rejected", "failed"):
                        return "__end__"

                    # Evaluate routing rules
                    eval_ctx = {
                        **state.get("input_data", {}),
                        **state.get("agent_outputs", {}).get(state.get("current_agent", ""), {}),
                        "confidence": state.get("confidence", 1.0),
                    }

                    for rule in agent_rules:
                        if rule.condition_type == "default":
                            return "END" if rule.to_agent == "END" else rule.to_agent
                        elif rule.condition_type == "conditional" and rule.condition_expression:
                            if safe_evaluate_condition(rule.condition_expression, eval_ctx):
                                return "END" if rule.to_agent == "END" else rule.to_agent

                    return "__end__"

                return route_next

            builder.add_conditional_edges(
                source_agent,
                make_router(rules_for_agent),
                path_map,
            )

        return builder.compile(checkpointer=checkpointer)

    def _create_agent_node(self, agent_def):
        """Factory creating the execution function for a specific agent node."""

        async def agent_node(state: AgentGraphState) -> AgentGraphState:
            agent_name = agent_def.name
            run_id = state["run_id"]
            session_id = state["session_id"]
            timestamp = datetime.now(timezone.utc).isoformat()

            with tracer.start_as_current_span(
                f"agent.{agent_name}",
                attributes={
                    "run_id": run_id,
                    "session_id": session_id,
                    "domain_pack": self.pack.name,
                    "agent_name": agent_name,
                },
            ) as span:
                logger.info("[%s] Executing agent node: %s", run_id, agent_name)

                # Prepare context for tool invocations
                tool_ctx = ToolContext(
                    run_id=run_id,
                    session_id=session_id,
                    memory_store=self.memory_store,
                    llm_provider=self.llm_provider,
                    verifier_url=self.verifier_url,
                )

                # Prompt construction
                prior_outputs_str = json.dumps(state.get("agent_outputs", {}), indent=2)
                prompt = (
                    f"Domain Workflow: {self.pack.name} (v{self.pack.version})\n"
                    f"Agent: {agent_name} ({agent_def.role})\n\n"
                    f"Initial Input Data:\n{json.dumps(state['input_data'], indent=2)}\n\n"
                    f"Outputs from previous agents:\n{prior_outputs_str}\n\n"
                    f"Allowed Tools: {agent_def.allowed_tools}\n"
                    f"Execute your role and return your decision, confidence, and any tool calls."
                )

                # Call LLM
                raw_llm_response = await self.llm_provider.generate(
                    prompt=prompt,
                    system_prompt=agent_def.system_prompt,
                )

                # Parse response
                try:
                    parsed_output = extract_json_from_text(raw_llm_response)
                except Exception as exc:
                    logger.warning("Failed to parse JSON from LLM: %s; using fallback wrapper", exc)
                    parsed_output = {
                        "agent_name": agent_name,
                        "raw_response": raw_llm_response,
                        "confidence": 0.80,
                    }

                confidence = float(parsed_output.get("confidence", 0.85))
                span.set_attribute("confidence", confidence)

                # Tool executions
                tool_calls_to_run = parsed_output.get("tool_calls", [])
                executed_tool_records: List[ToolCallRecord] = []

                for tc in tool_calls_to_run:
                    t_name = tc.get("tool") or tc.get("tool_name")
                    t_args = tc.get("arguments") or tc.get("args") or {}

                    if t_name and t_name in agent_def.allowed_tools:
                        tool_res = await self.tool_registry.invoke(t_name, t_args, tool_ctx)
                        executed_tool_records.append(
                            ToolCallRecord(
                                tool_name=t_name,
                                input_arguments=t_args,
                                output=tool_res.data,
                                execution_time_ms=tool_res.execution_time_ms,
                                error=tool_res.error,
                            )
                        )
                        # Incorporate tool result into agent output
                        if "tool_results" not in parsed_output:
                            parsed_output["tool_results"] = {}
                        parsed_output["tool_results"][t_name] = (
                            tool_res.data if tool_res.success else {"error": tool_res.error}
                        )
                    elif t_name:
                        executed_tool_records.append(
                            ToolCallRecord(
                                tool_name=t_name,
                                input_arguments=t_args,
                                output=None,
                                execution_time_ms=0.0,
                                error=f"Tool '{t_name}' not in agent's allowed_tools: {agent_def.allowed_tools}",
                            )
                        )

                # Confidence and Escalation Checks
                agent_threshold = self.pack.confidence_thresholds.get(
                    agent_name, self.pack.default_confidence_threshold
                )
                escalation_triggered = False
                escalation_reason = None

                # 1. Threshold check
                if confidence < agent_threshold:
                    escalation_triggered = True
                    escalation_reason = (
                        f"Agent '{agent_name}' confidence ({confidence:.2f}) is below "
                        f"domain safety threshold ({agent_threshold:.2f})."
                    )

                # 2. Rule evaluation
                eval_ctx = {
                    **state["input_data"],
                    **parsed_output,
                    "confidence": confidence,
                    "threshold": agent_threshold,
                }
                for rule in self.pack.escalation_rules:
                    if rule.auto_escalate and safe_evaluate_condition(rule.condition, eval_ctx):
                        escalation_triggered = True
                        escalation_reason = rule.reason
                        break

                # Update State
                new_state = dict(state)
                new_state["current_agent"] = agent_name
                new_state["confidence"] = confidence

                # Record step trace
                step_idx = len(new_state.get("trace_steps", [])) + 1
                step_trace = StepTrace(
                    step_index=step_idx,
                    agent_name=agent_name,
                    timestamp=timestamp,
                    input_data=state["input_data"],
                    output_data=parsed_output,
                    confidence=confidence,
                    tool_calls=executed_tool_records,
                    escalation_triggered=escalation_triggered,
                    escalation_reason=escalation_reason,
                )

                current_traces = list(new_state.get("trace_steps", []))
                current_traces.append(step_trace.model_dump())
                new_state["trace_steps"] = current_traces

                current_agent_outputs = dict(new_state.get("agent_outputs", {}))
                current_agent_outputs[agent_name] = parsed_output
                new_state["agent_outputs"] = current_agent_outputs

                if escalation_triggered:
                    logger.warning("[%s] Escalation triggered at agent '%s': %s", run_id, agent_name, escalation_reason)
                    new_state["status"] = "awaiting_approval"
                    new_state["pending_approval"] = True
                    new_state["escalation_reason"] = escalation_reason
                    span.set_attribute("escalation.triggered", True)
                    span.set_attribute("escalation.reason", escalation_reason)
                else:
                    span.set_attribute("escalation.triggered", False)
                    # Check if this agent transitions to END
                    rules_to_end = [
                        r for r in self.pack.routing_rules
                        if r.from_agent == agent_name and r.to_agent == "END"
                    ]
                    if rules_to_end:
                        new_state["status"] = "completed"
                        new_state["final_output"] = (
                            parsed_output.get("final_response") or parsed_output
                        )

                return new_state

        return agent_node

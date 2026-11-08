"""Pydantic schemas for domain packs, workflows, and tool execution."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RunStatusEnum(str, Enum):
    """Workflow execution lifecycle statuses."""

    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


# --- Domain Pack Specification Schemas ---


class AgentDefinition(BaseModel):
    """Definition of an individual agent node in a domain pack."""

    name: str = Field(..., description="Unique identifier for the agent node")
    role: str = Field(..., description="Business role or responsibility")
    system_prompt: str = Field(..., description="System instructions for the agent LLM")
    allowed_tools: List[str] = Field(
        default_factory=list, description="Tool names this agent is authorized to invoke"
    )


class RoutingRule(BaseModel):
    """Routing transition between agents in a domain pack."""

    from_agent: str = Field(..., description="Source agent node")
    condition_type: str = Field(
        default="default",
        description="Routing condition strategy: 'default', 'conditional', or 'regex'",
    )
    condition_expression: Optional[str] = Field(
        default=None, description="Optional condition expression to evaluate"
    )
    to_agent: str = Field(..., description="Destination agent node or 'END'")


class EscalationRule(BaseModel):
    """Escalation trigger condition requiring human operator review."""

    condition: str = Field(
        ..., description="Condition expression evaluated against state/confidence"
    )
    reason: str = Field(..., description="Human-readable justification for escalation")
    auto_escalate: bool = Field(
        default=True,
        description="Whether to immediately pause execution for human approval",
    )


class DomainPack(BaseModel):
    """Declarative specification defining a multi-agent business domain workflow."""

    name: str = Field(..., description="Domain pack identifier (e.g., it_ticket_triage)")
    version: str = Field(default="1.0.0", description="Semantic version of pack")
    description: str = Field(
        ..., description="Description of the domain workflow and scope"
    )
    default_confidence_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Global threshold below which human approval is mandated",
    )
    entry_agent: str = Field(..., description="The initial agent node to execute")
    confidence_thresholds: Dict[str, float] = Field(
        default_factory=dict,
        description="Agent-specific confidence threshold overrides",
    )
    agents: List[AgentDefinition] = Field(
        ..., min_length=1, description="List of agents participating in the workflow"
    )
    routing_rules: List[RoutingRule] = Field(
        ..., min_length=1, description="Transitions between agents"
    )
    escalation_rules: List[EscalationRule] = Field(
        default_factory=list,
        description="Rules determining when to pause for human intervention",
    )


class PackSummary(BaseModel):
    """High-level summary of a registered domain pack."""

    name: str
    version: str
    description: str
    default_confidence_threshold: float
    entry_agent: str
    agents: List[str]


# --- Workflow Run and Trace Schemas ---


class ToolCallRecord(BaseModel):
    """Audit record of a structured tool invocation within an agent step."""

    tool_name: str
    input_arguments: Dict[str, Any]
    output: Any
    execution_time_ms: float
    error: Optional[str] = None


class StepTrace(BaseModel):
    """Detailed audit trace for a single agent node execution."""

    step_index: int
    agent_name: str
    timestamp: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    confidence: float
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    escalation_triggered: bool = False
    escalation_reason: Optional[str] = None


class RunCreateRequest(BaseModel):
    """Request payload to initiate a domain workflow run."""

    pack_name: str = Field(..., description="Name of the registered domain pack to run")
    input_data: Dict[str, Any] = Field(
        ..., description="Initial input payload (e.g. ticket, loan request)"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier for stateful long-term memory lookup",
    )
    initial_agent: Optional[str] = Field(
        default=None,
        description="Optional entry agent override",
    )


class ApprovalRequest(BaseModel):
    """Request payload to approve a paused human-in-the-loop workflow run."""

    edited_output: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional edited final output providing operator overrides",
    )
    notes: Optional[str] = Field(
        default=None, description="Human reviewer justification notes"
    )


class RejectRequest(BaseModel):
    """Request payload to reject a paused human-in-the-loop workflow run."""

    reason: str = Field(..., description="Mandatory reason for rejection")


class RunResponse(BaseModel):
    """Detailed response representation of a workflow run."""

    run_id: str
    session_id: str
    pack_name: str
    status: RunStatusEnum
    confidence: float
    current_agent: Optional[str] = None
    input_data: Dict[str, Any]
    final_output: Optional[Dict[str, Any]] = None
    escalation_reason: Optional[str] = None
    trace_steps: List[StepTrace] = Field(default_factory=list)
    created_at: str
    updated_at: str

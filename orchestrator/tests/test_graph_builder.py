"""Unit tests for Dynamic LangGraph building and multi-agent execution."""

import pytest
from app.graph_builder import DynamicGraphBuilder
from app.llm.mock import MockLLM
from app.memory import SessionMemoryStore, create_sqlite_checkpointer
from app.packs import DomainPackManager
from app.tools.registry import ToolRegistry


@pytest.fixture
def manager(packs_dir):
    return DomainPackManager(packs_dir=packs_dir)


@pytest.fixture
def tool_registry():
    return ToolRegistry()


@pytest.fixture
def mock_llm():
    return MockLLM(latency_seconds=0.0)


@pytest.fixture
def memory_store():
    return SessionMemoryStore(db_path=":memory:")


@pytest.mark.asyncio
async def test_build_and_run_it_ticket_workflow(
    manager, tool_registry, mock_llm, memory_store
):
    """Verify IT ticket triage graph executes through all nodes to completion."""
    pack = manager.get_pack("it_ticket_triage")
    checkpointer = create_sqlite_checkpointer(":memory:")
    builder = DynamicGraphBuilder(
        pack=pack,
        tool_registry=tool_registry,
        llm_provider=mock_llm,
        memory_store=memory_store,
    )
    graph = builder.build(checkpointer=checkpointer)

    run_id = "test-it-run-1"
    initial_state = {
        "run_id": run_id,
        "session_id": "session-it-1",
        "pack_name": pack.name,
        "input_data": {
            "ticket_id": "INC-1001",
            "issue": "Cannot connect to VPN from home office",
            "user": "alice@company.com",
        },
        "agent_outputs": {},
        "current_agent": pack.entry_agent,
        "next_agent": None,
        "confidence": 1.0,
        "status": "running",
        "escalation_reason": None,
        "pending_approval": False,
        "trace_steps": [],
        "final_output": None,
    }

    final_state = await graph.ainvoke(
        initial_state, config={"configurable": {"thread_id": run_id}}
    )

    assert final_state["status"] == "completed"
    assert len(final_state["trace_steps"]) == 3
    agents_executed = [s["agent_name"] for s in final_state["trace_steps"]]
    assert agents_executed == ["classifier", "resolver", "reviewer"]
    assert final_state["final_output"] is not None


@pytest.mark.asyncio
async def test_build_and_run_loan_workflow(
    manager, tool_registry, mock_llm, memory_store
):
    """Verify loan prescreening graph runs through intake, underwriting, and compliance."""
    pack = manager.get_pack("loan_prescreening")
    checkpointer = create_sqlite_checkpointer(":memory:")
    builder = DynamicGraphBuilder(
        pack=pack,
        tool_registry=tool_registry,
        llm_provider=mock_llm,
        memory_store=memory_store,
    )
    graph = builder.build(checkpointer=checkpointer)

    run_id = "test-loan-run-1"
    initial_state = {
        "run_id": run_id,
        "session_id": "session-loan-1",
        "pack_name": pack.name,
        "input_data": {
            "applicant_name": "Jane Doe",
            "applicant_id": "APP-501",
            "loan_amount": 400000,
        },
        "agent_outputs": {},
        "current_agent": pack.entry_agent,
        "next_agent": None,
        "confidence": 1.0,
        "status": "running",
        "escalation_reason": None,
        "pending_approval": False,
        "trace_steps": [],
        "final_output": None,
    }

    final_state = await graph.ainvoke(
        initial_state, config={"configurable": {"thread_id": run_id}}
    )

    assert final_state["status"] == "completed"
    assert len(final_state["trace_steps"]) == 3
    agents_executed = [s["agent_name"] for s in final_state["trace_steps"]]
    assert agents_executed == ["intake", "underwriter", "compliance"]


@pytest.mark.asyncio
async def test_escalation_on_low_confidence(
    manager, tool_registry, mock_llm, memory_store
):
    """Verify low agent confidence triggers human escalation pause."""
    pack = manager.get_pack("it_ticket_triage")
    checkpointer = create_sqlite_checkpointer(":memory:")
    builder = DynamicGraphBuilder(
        pack=pack,
        tool_registry=tool_registry,
        llm_provider=mock_llm,
        memory_store=memory_store,
    )
    graph = builder.build(checkpointer=checkpointer)

    run_id = "test-low-conf-1"
    # Prompt keyword 'low_confidence' causes MockLLM to return 0.55 confidence (< threshold)
    initial_state = {
        "run_id": run_id,
        "session_id": "session-low-1",
        "pack_name": pack.name,
        "input_data": {
            "ticket_id": "INC-9999",
            "issue": "low_confidence unusual kernel bug",
        },
        "agent_outputs": {},
        "current_agent": pack.entry_agent,
        "next_agent": None,
        "confidence": 1.0,
        "status": "running",
        "escalation_reason": None,
        "pending_approval": False,
        "trace_steps": [],
        "final_output": None,
    }

    final_state = await graph.ainvoke(
        initial_state, config={"configurable": {"thread_id": run_id}}
    )

    assert final_state["status"] == "awaiting_approval"
    assert final_state["pending_approval"] is True
    assert "below domain safety threshold" in final_state["escalation_reason"]


@pytest.mark.asyncio
async def test_escalation_on_critical_incident_rule(
    manager, tool_registry, mock_llm, memory_store
):
    """Verify critical security escalation rule triggers human operator sign-off."""
    pack = manager.get_pack("it_ticket_triage")
    checkpointer = create_sqlite_checkpointer(":memory:")
    builder = DynamicGraphBuilder(
        pack=pack,
        tool_registry=tool_registry,
        llm_provider=mock_llm,
        memory_store=memory_store,
    )
    graph = builder.build(checkpointer=checkpointer)

    run_id = "test-security-crit-1"
    # Prompt keyword 'critical' triggers MockLLM urgency='Critical'
    initial_state = {
        "run_id": run_id,
        "session_id": "session-crit-1",
        "pack_name": pack.name,
        "input_data": {
            "ticket_id": "INC-CRIT-9",
            "issue": "critical root password breach",
        },
        "agent_outputs": {},
        "current_agent": pack.entry_agent,
        "next_agent": None,
        "confidence": 1.0,
        "status": "running",
        "escalation_reason": None,
        "pending_approval": False,
        "trace_steps": [],
        "final_output": None,
    }

    final_state = await graph.ainvoke(
        initial_state, config={"configurable": {"thread_id": run_id}}
    )

    assert final_state["status"] == "awaiting_approval"
    assert final_state["pending_approval"] is True
    assert "Critical urgency or security incidents require human technician sign-off" in final_state["escalation_reason"]

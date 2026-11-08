"""Enterprise Agent Platform Orchestrator FastAPI Application."""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings
from app.graph_builder import DynamicGraphBuilder
from app.llm import get_llm_provider
from app.memory import SessionMemoryStore, create_sqlite_checkpointer
from app.packs import DomainPackManager
from app.schemas import (
    ApprovalRequest,
    DomainPack,
    PackSummary,
    RejectRequest,
    RunCreateRequest,
    RunResponse,
    RunStatusEnum,
)
from app.telemetry import configure_structured_logging, setup_telemetry
from app.tools.registry import ToolRegistry
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

logger = logging.getLogger(__name__)


# Global singletons
pack_manager: Optional[DomainPackManager] = None
tool_registry: Optional[ToolRegistry] = None
memory_store: Optional[SessionMemoryStore] = None
checkpointer: Optional[Any] = None
llm_provider: Optional[Any] = None
runs_database: Dict[str, RunResponse] = {}
tracer: Optional[trace.Tracer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager initializing platform dependencies on startup."""
    global pack_manager, tool_registry, memory_store, checkpointer, llm_provider, tracer

    # 1. Observability setup
    configure_structured_logging(settings.log_level)
    tracer = setup_telemetry(
        service_name=settings.otel_service_name,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
    )
    HTTPXClientInstrumentor().instrument()

    # 2. Memory and Persistence
    if settings.data_dir == ":memory:":
        db_path = ":memory:"
        cp_path = ":memory:"
    else:
        db_path = f"{settings.data_dir}/session_memory.db"
        cp_path = f"{settings.data_dir}/checkpoints.db"

    memory_store = SessionMemoryStore(db_path=db_path)
    checkpointer = create_sqlite_checkpointer(db_path=cp_path)

    # 3. Tool Registry
    tool_registry = ToolRegistry()

    # 4. LLM Provider
    llm_provider = get_llm_provider(
        provider_name=settings.llm_provider,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        mock_latency=settings.llm_mock_latency,
    )

    # 5. Domain Pack Manager
    pack_manager = DomainPackManager(packs_dir=settings.domain_packs_dir)

    logger.info(
        "Orchestrator initialized successfully with %d domain packs: %s",
        len(pack_manager.list_packs()),
        [p.name for p in pack_manager.list_packs()],
    )

    yield

    # Cleanup
    if memory_store:
        memory_store.close()
    logger.info("Orchestrator shut down cleanly.")


app = FastAPI(
    title="Enterprise Agent Platform - Orchestrator",
    description="Multi-agent workflow orchestration with dynamic domain packs, stateful memory, and human-in-the-loop.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend web application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenTelemetry auto-instrumentation for incoming requests
FastAPIInstrumentor.instrument_app(app)


# --- API Endpoints ---


@app.get("/health", tags=["System"])
async def health_check():
    """Service health and diagnostic status."""
    return {
        "status": "ok",
        "service": "orchestrator",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "packs_loaded": len(pack_manager.list_packs()) if pack_manager else 0,
        "llm_provider": settings.llm_provider,
    }


@app.get("/packs", response_model=List[PackSummary], tags=["Domain Packs"])
async def list_domain_packs():
    """Retrieve all loaded and validated domain packs."""
    if not pack_manager:
        raise HTTPException(status_code=500, detail="Pack manager not initialized")
    return pack_manager.list_packs()


@app.get("/packs/{name}", response_model=DomainPack, tags=["Domain Packs"])
async def get_domain_pack(name: str):
    """Retrieve the full YAML specification schema for a specific domain pack."""
    if not pack_manager:
        raise HTTPException(status_code=500, detail="Pack manager not initialized")
    pack = pack_manager.get_pack(name)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Domain pack '{name}' not found")
    return pack


@app.post("/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED, tags=["Workflows"])
async def create_run(req: RunCreateRequest):
    """Initiate an asynchronous domain agent workflow run."""
    if not pack_manager:
        raise HTTPException(status_code=500, detail="Pack manager not initialized")

    pack = pack_manager.get_pack(req.pack_name)
    if not pack:
        raise HTTPException(
            status_code=404,
            detail=f"Domain pack '{req.pack_name}' not found. Available: {[p.name for p in pack_manager.list_packs()]}",
        )

    run_id = str(uuid.uuid4())
    session_id = req.session_id or str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()

    # OpenTelemetry workflow root span
    with tracer.start_as_current_span(
        "workflow.run",
        attributes={
            "run_id": run_id,
            "session_id": session_id,
            "domain_pack": pack.name,
        },
    ) as root_span:
        logger.info("Starting workflow run %s for pack %s", run_id, pack.name)

        # Build dynamic graph
        builder = DynamicGraphBuilder(
            pack=pack,
            tool_registry=tool_registry,
            llm_provider=llm_provider,
            memory_store=memory_store,
            verifier_url=settings.verifier_url,
        )
        graph = builder.build(checkpointer=checkpointer)

        initial_state = {
            "run_id": run_id,
            "session_id": session_id,
            "pack_name": pack.name,
            "input_data": req.input_data,
            "agent_outputs": {},
            "current_agent": req.initial_agent or pack.entry_agent,
            "next_agent": None,
            "confidence": 1.0,
            "status": "running",
            "escalation_reason": None,
            "pending_approval": False,
            "trace_steps": [],
            "final_output": None,
        }

        # Execute graph
        config = {"configurable": {"thread_id": run_id}}
        final_state = await graph.ainvoke(initial_state, config=config)

        run_status = RunStatusEnum(final_state.get("status", "completed"))
        root_span.set_attribute("workflow.status", run_status.value)
        root_span.set_attribute("workflow.confidence", float(final_state.get("confidence", 1.0)))

        run_resp = RunResponse(
            run_id=run_id,
            session_id=session_id,
            pack_name=pack.name,
            status=run_status,
            confidence=float(final_state.get("confidence", 1.0)),
            current_agent=final_state.get("current_agent"),
            input_data=req.input_data,
            final_output=final_state.get("final_output"),
            escalation_reason=final_state.get("escalation_reason"),
            trace_steps=final_state.get("trace_steps", []),
            created_at=now_str,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        runs_database[run_id] = run_resp
        return run_resp


@app.get("/runs", response_model=List[RunResponse], tags=["Workflows"])
async def list_runs():
    """List all workflow runs ordered by creation time descending."""
    return sorted(list(runs_database.values()), key=lambda r: r.created_at, reverse=True)


@app.get("/runs/{run_id}", response_model=RunResponse, tags=["Workflows"])
async def get_run(run_id: str):
    """Retrieve full audit trace and status for a specific workflow run."""
    run = runs_database.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return run


@app.post("/runs/{run_id}/approve", response_model=RunResponse, tags=["Human In The Loop"])
async def approve_run(run_id: str, req: ApprovalRequest):
    """Approve a paused run awaiting human sign-off with optional output edits."""
    run = runs_database.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    if run.status != RunStatusEnum.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Run '{run_id}' is in status '{run.status.value}', cannot approve",
        )

    pack = pack_manager.get_pack(run.pack_name)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Domain pack '{run.pack_name}' not found")

    with tracer.start_as_current_span(
        "workflow.approval",
        attributes={"run_id": run_id, "action": "approved"},
    ):
        logger.info("Human operator approved run %s (notes: %s)", run_id, req.notes)

        # Finalize run
        run.status = RunStatusEnum.COMPLETED
        if req.edited_output:
            run.final_output = req.edited_output
        elif not run.final_output:
            # Use last step's output as approved final output
            last_trace = run.trace_steps[-1] if run.trace_steps else None
            if last_trace:
                out = last_trace.output_data
                run.final_output = out.get("final_response") or out

        run.updated_at = datetime.now(timezone.utc).isoformat()
        runs_database[run_id] = run
        return run


@app.post("/runs/{run_id}/reject", response_model=RunResponse, tags=["Human In The Loop"])
async def reject_run(run_id: str, req: RejectRequest):
    """Reject a paused run with operator-provided rationale."""
    run = runs_database.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    if run.status != RunStatusEnum.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Run '{run_id}' is in status '{run.status.value}', cannot reject",
        )

    with tracer.start_as_current_span(
        "workflow.rejection",
        attributes={"run_id": run_id, "action": "rejected", "reason": req.reason},
    ):
        logger.info("Human operator rejected run %s: %s", run_id, req.reason)
        run.status = RunStatusEnum.REJECTED
        run.escalation_reason = f"Rejected by human operator: {req.reason}"
        run.updated_at = datetime.now(timezone.utc).isoformat()
        runs_database[run_id] = run
        return run

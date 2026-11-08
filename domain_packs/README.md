# Domain Packs Guide

Domain packs allow organizations to define multi-agent business workflows in declarative YAML without changing any platform code. The platform loads packs, validates them via Pydantic schemas, and dynamically compiles them into stateful LangGraph workflows.

## Schema Overview

Each domain pack must conform to the following top-level schema:

```yaml
name: string                      # Unique identifier for the domain pack (e.g. it_ticket_triage)
version: string                   # Semantic version (e.g. 1.0.0)
description: string               # Concise summary of workflow purpose
default_confidence_threshold: float # Baseline threshold (0.0 - 1.0) for human escalation
entry_agent: string               # Starting agent node name

# Optional agent-specific thresholds
confidence_thresholds:
  agent_name: float

# List of agents participating in the workflow
agents:
  - name: string                  # Unique node identifier
    role: string                  # High-level responsibility description
    system_prompt: string         # Instructions provided to the agent
    allowed_tools:                # Registered tool identifiers this agent may invoke
      - tool_name

# Routing transitions between agents
routing_rules:
  - from_agent: string            # Source agent
    condition_type: default       # default, conditional, or regex
    to_agent: string              # Target agent or 'END'

# Escalation rules that trigger Human-in-the-Loop review
escalation_rules:
  - condition: string             # Expression evaluated against workflow state or confidence
    reason: string                # Explanation surfaced to human operator in UI
    auto_escalate: bool           # Whether to pause workflow into awaiting_approval
```

## Adding a New Domain Pack

1. Create a new YAML file in the `domain_packs/` directory (e.g. `domain_packs/customer_onboarding.yaml`).
2. Define the agents, their system prompts, and tool permissions from the tool registry (`search_kb`, `calculate`, `lookup_record`, `memory_read`, `memory_write`, `generate_code`).
3. Define the sequential or conditional routing transitions. Use `END` to terminate the workflow.
4. Define escalation rules for low confidence, regulatory boundaries, or high-risk inputs.
5. Save the file. The orchestrator automatically loads all valid YAML files on startup or when `GET /packs` is queried.

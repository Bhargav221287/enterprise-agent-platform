"""Unit tests for domain pack schema validation and manager."""

import pytest
import yaml
from app.packs import DomainPackManager
from app.schemas import DomainPack


def test_load_valid_it_ticket_pack(packs_dir):
    """Verify it_ticket_triage.yaml loads and validates successfully."""
    manager = DomainPackManager(packs_dir=packs_dir)
    pack = manager.get_pack("it_ticket_triage")

    assert pack is not None
    assert pack.name == "it_ticket_triage"
    assert pack.version == "1.0.0"
    assert pack.entry_agent == "classifier"
    assert len(pack.agents) == 3
    assert len(pack.routing_rules) >= 3
    assert len(pack.escalation_rules) >= 2


def test_load_valid_loan_prescreening_pack(packs_dir):
    """Verify loan_prescreening.yaml loads and validates successfully."""
    manager = DomainPackManager(packs_dir=packs_dir)
    pack = manager.get_pack("loan_prescreening")

    assert pack is not None
    assert pack.name == "loan_prescreening"
    assert pack.entry_agent == "intake"
    assert len(pack.agents) == 3
    assert "calculate" in pack.agents[1].allowed_tools


def test_invalid_pack_missing_fields(tmp_path):
    """Verify validation fails when mandatory fields are omitted."""
    invalid_data = {
        "name": "incomplete_pack",
        # missing version, description, entry_agent, agents, routing_rules
    }
    file_path = tmp_path / "invalid.yaml"
    with open(file_path, "w") as f:
        yaml.dump(invalid_data, f)

    manager = DomainPackManager(packs_dir=tmp_path)
    with pytest.raises(ValueError, match="Domain pack schema validation failed"):
        manager.load_pack_from_file(file_path)


def test_invalid_entry_agent_reference(tmp_path):
    """Verify error when entry_agent is not in the declared agents list."""
    invalid_data = {
        "name": "bad_entry",
        "version": "1.0.0",
        "description": "Test pack with bad entry agent",
        "default_confidence_threshold": 0.8,
        "entry_agent": "non_existent_agent",
        "agents": [
            {
                "name": "worker",
                "role": "Worker role",
                "system_prompt": "Do work",
                "allowed_tools": [],
            }
        ],
        "routing_rules": [
            {"from_agent": "worker", "condition_type": "default", "to_agent": "END"}
        ],
    }
    file_path = tmp_path / "bad_entry.yaml"
    with open(file_path, "w") as f:
        yaml.dump(invalid_data, f)

    manager = DomainPackManager(packs_dir=tmp_path)
    with pytest.raises(ValueError, match="Entry agent 'non_existent_agent' is not declared"):
        manager.load_pack_from_file(file_path)


def test_invalid_routing_rule_target(tmp_path):
    """Verify error when routing rule points to an unknown agent."""
    invalid_data = {
        "name": "bad_routing",
        "version": "1.0.0",
        "description": "Test pack with invalid route target",
        "default_confidence_threshold": 0.8,
        "entry_agent": "agent1",
        "agents": [
            {
                "name": "agent1",
                "role": "Role 1",
                "system_prompt": "Prompt 1",
                "allowed_tools": [],
            }
        ],
        "routing_rules": [
            {"from_agent": "agent1", "condition_type": "default", "to_agent": "ghost_agent"}
        ],
    }
    file_path = tmp_path / "bad_route.yaml"
    with open(file_path, "w") as f:
        yaml.dump(invalid_data, f)

    manager = DomainPackManager(packs_dir=tmp_path)
    with pytest.raises(ValueError, match="is neither 'END' nor an agent"):
        manager.load_pack_from_file(file_path)


def test_confidence_threshold_bounds():
    """Verify confidence threshold is strictly constrained between 0.0 and 1.0."""
    valid_data = {
        "name": "bounds_test",
        "version": "1.0.0",
        "description": "Test threshold bounds",
        "default_confidence_threshold": 1.5,  # Exceeds max 1.0
        "entry_agent": "worker",
        "agents": [
            {"name": "worker", "role": "Worker", "system_prompt": "Do", "allowed_tools": []}
        ],
        "routing_rules": [
            {"from_agent": "worker", "condition_type": "default", "to_agent": "END"}
        ],
    }
    with pytest.raises(Exception):
        DomainPack(**valid_data)

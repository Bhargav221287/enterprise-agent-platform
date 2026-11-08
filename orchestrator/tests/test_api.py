"""Integration tests for Orchestrator REST API endpoints."""

from app.schemas import RunStatusEnum


def test_api_health(test_client):
    """Verify /health returns 200 OK and loaded pack count."""
    resp = test_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["packs_loaded"] >= 2


def test_api_list_and_get_packs(test_client):
    """Verify /packs and /packs/{name} endpoints."""
    resp = test_client.get("/packs")
    assert resp.status_code == 200
    packs = resp.json()
    assert len(packs) >= 2
    pack_names = [p["name"] for p in packs]
    assert "it_ticket_triage" in pack_names
    assert "loan_prescreening" in pack_names

    resp_single = test_client.get("/packs/it_ticket_triage")
    assert resp_single.status_code == 200
    assert resp_single.json()["entry_agent"] == "classifier"


def test_api_create_and_complete_run(test_client):
    """Verify POST /runs creates and executes a complete workflow."""
    payload = {
        "pack_name": "it_ticket_triage",
        "input_data": {
            "ticket_id": "INC-8080",
            "issue": "Cannot connect to external monitor",
            "user": "developer@company.com",
        },
    }
    resp = test_client.post("/runs", json=payload)
    assert resp.status_code == 201
    run = resp.json()

    assert run["run_id"] is not None
    assert run["status"] == RunStatusEnum.COMPLETED.value
    assert len(run["trace_steps"]) == 3
    assert run["final_output"] is not None

    # Verify GET /runs/{id}
    get_resp = test_client.get(f"/runs/{run['run_id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["run_id"] == run["run_id"]


def test_api_approval_flow(test_client):
    """Verify human-in-the-loop escalation pause and approval resolution."""
    # Create run with keyword triggering escalation
    payload = {
        "pack_name": "it_ticket_triage",
        "input_data": {
            "ticket_id": "INC-SEC-01",
            "issue": "critical security vulnerability detected in auth service",
        },
    }
    resp = test_client.post("/runs", json=payload)
    assert resp.status_code == 201
    run = resp.json()

    assert run["status"] == RunStatusEnum.AWAITING_APPROVAL.value
    assert run["escalation_reason"] is not None

    # Approve run with edited output
    approve_payload = {
        "edited_output": {"resolution": "Manual patch applied by senior security engineer."},
        "notes": "Verified hotfix and tested in staging.",
    }
    approve_resp = test_client.post(f"/runs/{run['run_id']}/approve", json=approve_payload)
    assert approve_resp.status_code == 200
    approved_run = approve_resp.json()

    assert approved_run["status"] == RunStatusEnum.COMPLETED.value
    assert approved_run["final_output"]["resolution"] == "Manual patch applied by senior security engineer."


def test_api_reject_flow(test_client):
    """Verify human-in-the-loop escalation pause and rejection."""
    payload = {
        "pack_name": "it_ticket_triage",
        "input_data": {
            "ticket_id": "INC-SEC-02",
            "issue": "critical privilege escalation attack",
        },
    }
    resp = test_client.post("/runs", json=payload)
    run = resp.json()
    assert run["status"] == RunStatusEnum.AWAITING_APPROVAL.value

    # Reject run
    reject_payload = {"reason": "Incident requires forensic investigation before automated actions."}
    reject_resp = test_client.post(f"/runs/{run['run_id']}/reject", json=reject_payload)
    assert reject_resp.status_code == 200
    rejected_run = reject_resp.json()

    assert rejected_run["status"] == RunStatusEnum.REJECTED.value
    assert "forensic investigation" in rejected_run["escalation_reason"]

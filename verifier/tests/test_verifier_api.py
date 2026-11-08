"""Integration tests for Verifier Service REST API."""


def test_verifier_health(test_client):
    """Verify GET /health returns 200 OK."""
    resp = test_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_verifier_verify_success(test_client):
    """Verify POST /verify returns passed report for clean code."""
    payload = {
        "code": "def double(x: int) -> int:\n    return x * 2\n",
        "test_cases": [
            {"input": {"x": 5}, "expected_output": 10},
            {"input": {"x": -3}, "expected_output": -6},
        ],
    }
    resp = test_client.post("/verify", json=payload)
    assert resp.status_code == 200
    report = resp.json()

    assert report["passed"] is True
    assert len(report["checks"]) == 3
    assert all(c["passed"] for c in report["checks"])
    assert report["summary"]["tests_passed"] == 2


def test_verifier_verify_unsafe_code(test_client):
    """Verify POST /verify halts at safety stage when dangerous code is sent."""
    payload = {
        "code": "import subprocess\ndef pwn():\n    subprocess.run(['ls'])\n",
        "test_cases": [],
    }
    resp = test_client.post("/verify", json=payload)
    assert resp.status_code == 200
    report = resp.json()

    assert report["passed"] is False
    assert report["summary"]["stage_failed"] == "ast_safety_scan"
    assert any("subprocess" in v for v in report["summary"]["violations"])


def test_verifier_verify_syntax_error(test_client):
    """Verify POST /verify halts at syntax stage on invalid code."""
    payload = {
        "code": "def incomplete(x:\n    return x\n",
        "test_cases": [],
    }
    resp = test_client.post("/verify", json=payload)
    assert resp.status_code == 200
    report = resp.json()

    assert report["passed"] is False
    assert report["summary"]["stage_failed"] == "syntax_check"

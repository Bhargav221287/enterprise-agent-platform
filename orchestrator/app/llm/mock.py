"""Deterministic Mock LLM Provider for testing, CI, and micro-benchmarking."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class MockLLM(LLMProvider):
    """Deterministic, configurable latency mock LLM."""

    def __init__(self, latency_seconds: float = 0.001) -> None:
        self.latency_seconds = latency_seconds
        self.custom_responses: Dict[str, str] = {}
        self.call_history: List[Dict[str, Any]] = []
        self.fail_json_count = 0  # Useful for testing JSON retry logic

    def set_custom_response(self, keyword: str, response: str) -> None:
        """Register a specific mock text response when keyword appears in prompt."""
        self.custom_responses[keyword] = response

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate deterministic structured response based on agent prompt context."""
        if self.latency_seconds > 0:
            await asyncio.sleep(self.latency_seconds)

        self.call_history.append(
            {"prompt": prompt, "system_prompt": system_prompt, "schema": json_schema}
        )

        # Check for simulated malformed JSON count
        if self.fail_json_count > 0:
            self.fail_json_count -= 1
            return "This is invalid non-json text produced by LLM."

        # Check for user-registered custom overrides
        for kw, resp in self.custom_responses.items():
            if kw in prompt or kw in system_prompt:
                return resp

        # Check if generating pure Python code
        if "write a clean, self-contained python function" in prompt.lower() or "def " in prompt:
            return (
                "def sanitize_ticket_id(raw_id: str) -> str:\n"
                "    # Normalizes incident identifier\n"
                "    clean = raw_id.strip().upper()\n"
                "    return clean\n"
            )

        lower_prompt = prompt.lower()
        lower_sys = system_prompt.lower()

        # Domain: IT Ticket Triage
        if "classifier" in lower_sys or "classifier" in lower_prompt:
            urgency = "Critical" if ("critical" in lower_prompt or "security" in lower_prompt) else "Medium"
            category = "Access" if "vpn" in lower_prompt or "login" in lower_prompt else "Software/Bug"
            conf = 0.55 if "low_confidence" in lower_prompt else 0.88

            return json.dumps({
                "agent_name": "classifier",
                "category": category,
                "urgency": urgency,
                "confidence": conf,
                "tool_calls": [
                    {"tool": "search_kb", "arguments": {"query": f"{category} {urgency}"}}
                ],
                "reasoning": f"Identified issue as {category} with {urgency} urgency.",
                "summary": "Ticket categorized successfully",
            })

        if "resolver" in lower_sys or "resolver" in lower_prompt:
            conf = 0.55 if "low_confidence" in lower_prompt else 0.85
            is_bug = "bug" in lower_prompt or "reproduce" in lower_prompt

            tool_calls = [
                {"tool": "memory_write", "arguments": {"key": "last_resolved_action", "value": "flushed_dns"}}
            ]
            if is_bug:
                tool_calls.append({
                    "tool": "generate_code",
                    "arguments": {
                        "prompt": "Create a function to test database connection retry",
                        "test_cases": [{"input": {"host": "db.internal"}, "expected_output": {"status": "ok"}}],
                    },
                })

            return json.dumps({
                "agent_name": "resolver",
                "proposed_solution": "Followed KB-101: Cleared cache, restarted authentication agent.",
                "confidence": conf,
                "tool_calls": tool_calls,
                "reasoning": "Resolution steps mapped directly from KB article.",
                "summary": "Drafted remediation plan",
            })

        if "reviewer" in lower_sys or "reviewer" in lower_prompt:
            conf = 0.55 if "low_confidence" in lower_prompt else 0.92
            return json.dumps({
                "agent_name": "reviewer",
                "review_decision": "Approved",
                "confidence": conf,
                "tool_calls": [
                    {"tool": "calculate", "arguments": {"expression": "95 - 5"}}
                ],
                "final_response": {
                    "resolution": "Your ticket has been reviewed and resolved. Please restart your client.",
                    "status": "Resolved",
                    "sla_met": True,
                },
                "summary": "Safety and quality review verified.",
            })

        # Domain: Loan Prescreening
        if "intake" in lower_sys or "intake" in lower_prompt:
            conf = 0.55 if "low_confidence" in lower_prompt else 0.90
            app_id = "APP-502" if "bad_credit" in lower_prompt else "APP-501"
            return json.dumps({
                "agent_name": "intake",
                "applicant_id": app_id,
                "stated_income": 9500,
                "requested_amount": 450000,
                "confidence": conf,
                "tool_calls": [
                    {"tool": "lookup_record", "arguments": {"record_type": "credit_profile", "record_id": app_id}},
                    {"tool": "memory_write", "arguments": {"key": "applicant_id", "value": app_id}},
                ],
                "summary": "Intake completed and credit profile fetched.",
            })

        if "underwriter" in lower_sys or "underwriter" in lower_prompt:
            conf = 0.55 if "low_confidence" in lower_prompt else 0.88
            is_high_dti = "high_dti" in lower_prompt or "bad_credit" in lower_prompt
            expr = "(4500 / 8000) * 100" if is_high_dti else "(1800 / 9500) * 100"
            dti_val = 56.25 if is_high_dti else 18.95

            return json.dumps({
                "agent_name": "underwriter",
                "dti": dti_val,
                "ltv": 75.0,
                "credit_score": 610 if is_high_dti else 750,
                "preliminary_decision": "Declined" if is_high_dti else "Qualified",
                "confidence": conf,
                "tool_calls": [
                    {"tool": "calculate", "arguments": {"expression": expr}}
                ],
                "summary": f"Calculated DTI ratio: {dti_val}%.",
            })

        if "compliance" in lower_sys or "compliance" in lower_prompt:
            conf = 0.55 if "low_confidence" in lower_prompt else 0.94
            return json.dumps({
                "agent_name": "compliance",
                "compliance_status": "Passed",
                "confidence": conf,
                "tool_calls": [
                    {"tool": "memory_read", "arguments": {"key": "applicant_id"}}
                ],
                "final_response": {
                    "decision": "Conditionally Approved",
                    "maximum_loan": 450000,
                    "conforming_status": "Conforming",
                },
                "summary": "Compliance validation complete.",
            })

        # Generic default structured response
        return json.dumps({
            "agent_name": "generic_agent",
            "confidence": 0.85,
            "tool_calls": [],
            "reasoning": "Processed request successfully.",
            "final_response": {"message": "Workflow step processed", "input": prompt[:100]},
            "summary": "Completed step",
        })

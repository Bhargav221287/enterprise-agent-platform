"""Base LLM Provider interface with retry and JSON fallback recovery."""

import abc
import json
import logging
import re
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Extract and parse a JSON dictionary from free-form text or markdown code fences."""
    text = text.strip()
    if text.startswith("```"):
        # Match ```json ... ``` or ``` ... ```
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()

    # Try direct parse
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # Look for outermost matching curly braces
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start : end + 1]
        try:
            data = json.loads(snippet)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON object from model response: {text[:200]}")


class LLMProvider(abc.ABC):
    """Abstract interface defining LLM interaction capabilities."""

    @abc.abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a raw text completion."""
        raise NotImplementedError

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str,
        schema_cls: Type[BaseModel],
        max_retries: int = 2,
    ) -> BaseModel:
        """Generate and validate structured output conforming to a Pydantic model with retry/fallback."""
        schema = schema_cls.model_json_schema()
        instructions = (
            f"\n\nYou MUST respond with ONLY a valid JSON object matching this schema:\n"
            f"{json.dumps(schema, indent=2)}\n"
            "Do not output any additional prose outside the JSON object."
        )
        augmented_prompt = prompt + instructions

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                raw_response = await self.generate(
                    prompt=augmented_prompt,
                    system_prompt=system_prompt,
                    json_schema=schema,
                )
                parsed_dict = extract_json_from_text(raw_response)
                return schema_cls(**parsed_dict)
            except (ValueError, ValidationError, json.JSONDecodeError) as err:
                last_error = err
                logger.warning(
                    "JSON parsing/validation failed on attempt %d/%d: %s",
                    attempt + 1,
                    max_retries + 1,
                    err,
                )
                if attempt < max_retries:
                    augmented_prompt += f"\nPrevious attempt failed with error: {str(err)}. Return strict valid JSON."

        # Graceful fallback: attempt instantiation with default / partial values if schema allows
        try:
            return schema_cls()
        except Exception:
            raise ValueError(f"Model failed to produce valid JSON matching {schema_cls.__name__}: {last_error}")

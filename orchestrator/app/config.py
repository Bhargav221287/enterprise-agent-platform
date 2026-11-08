"""Configuration settings for the Enterprise Agent Platform Orchestrator."""

import os
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    """Runtime configuration settings."""

    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    host: str = os.getenv("ORCHESTRATOR_HOST", "0.0.0.0")
    port: int = int(os.getenv("ORCHESTRATOR_PORT", "8000"))

    verifier_url: str = os.getenv("VERIFIER_URL", "http://localhost:8001")
    domain_packs_dir: str = os.getenv(
        "DOMAIN_PACKS_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "domain_packs"),
    )
    data_dir: str = os.getenv(
        "DATA_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "data"),
    )

    llm_provider: str = os.getenv("LLM_PROVIDER", "mock")
    llm_model: str = os.getenv("LLM_MODEL", "mock-agent-v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "mock-key")
    llm_mock_latency: float = float(os.getenv("LLM_MOCK_LATENCY", "0.001"))

    otel_service_name: str = os.getenv("OTEL_SERVICE_NAME", "orchestrator-service")
    otel_exporter_otlp_endpoint: str = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318"
    )
    jaeger_ui_url: str = os.getenv("JAEGER_UI_URL", "http://localhost:16686")


settings = Settings()

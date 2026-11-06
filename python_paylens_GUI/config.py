from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bootstrap_servers: str
    api_key: str
    api_secret: str
    topic_auth_requests: str
    topic_auth_responses: str    
    topic_capture_expectations: str
    topic_capture_results: str
    topic_refund: str
    topic_order_fulfillment: str
    base_dir: Path


def load_settings(base_dir: Path | str | None = None) -> Settings:
    """Load application settings from the environment and `.env` file."""
    root = Path(base_dir) if base_dir else Path(__file__).resolve().parent
    env_path = root / ".env"
    load_dotenv(env_path, override=False)

    settings = Settings(
        bootstrap_servers=os.getenv("BOOTSTRAP_SERVERS", "").strip(),
        api_key=os.getenv("API_KEY", "").strip(),
        api_secret=os.getenv("API_SECRET", "").strip(),
        topic_auth_requests=os.getenv("TOPIC_AUTH_REQUESTS", "AUTH_REQUESTS").strip(),
        topic_auth_responses=os.getenv("TOPIC_AUTH_RESPONSES", "AUTH_RESPONSES").strip(),
        topic_capture_expectations=os.getenv("TOPIC_CAPTURE_EXPECTATIONS", "CAPTURE_EXPECTATIONS").strip(),
        topic_capture_results=os.getenv("TOPIC_CAPTURE_RESULTS", "CAPTURE_RESULTS").strip(),
        topic_refund=os.getenv("TOPIC_REFUND", "REFUND").strip(),
        topic_order_fulfillment=os.getenv("TOPIC_ORDER_FULFILLMENT", "ORDER_FULFILLMENT").strip(),
        base_dir=root,
    )
    validate_settings(settings)
    return settings


def validate_settings(settings: Settings) -> None:
    required = {
        "BOOTSTRAP_SERVERS": settings.bootstrap_servers,
        "API_KEY": settings.api_key,
        "API_SECRET": settings.api_secret,
        "TOPIC_AUTH_REQUESTS": settings.topic_auth_requests,
        "TOPIC_AUTH_RESPONSES": settings.topic_auth_responses,
        "TOPIC_CAPTURE_EXPECTATIONS": settings.topic_capture_expectations,
        "TOPIC_CAPTURE_RESULTS": settings.topic_capture_results,
        "TOPIC_REFUND": settings.topic_refund,
        "TOPIC_ORDER_FULFILLMENT": settings.topic_order_fulfillment
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(
            "Missing required environment variables: " + ", ".join(missing)
        )

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    sql_connection_string: str = ""
    eventhub_connection_string: str = ""


def load_settings(base_dir: Path | str | None = None) -> Settings:
    """Load application settings from the environment and `.env` file."""
    root = Path(base_dir) if base_dir else Path(__file__).resolve().parent
    env_path = root / ".env"
    load_dotenv(env_path, override=False)

    settings = Settings(
        base_dir=root,
        sql_connection_string=os.getenv("SQL_CONNECTION_STRING", "").strip(),
        eventhub_connection_string=os.getenv("EVENTHUB_CONNECTION_STRING", "").strip()
    )
    validate_settings(settings)
    return settings


def validate_settings(settings: Settings) -> None:
    required = {
        "EVENTHUB_CONNECTION_STRING": settings.eventhub_connection_string,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(
            "Missing required environment variables: " + ", ".join(missing)
        )

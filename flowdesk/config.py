"""Configuration settings for FlowDesk."""

import os
from pathlib import Path

from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseModel):
    app_name: str = "FlowDesk"
    database_url: str = os.getenv("FLOWDESK_DB_URL", f"sqlite:///{BASE_DIR / 'flowdesk.db'}")

    # LLM Settings (never hardcoded, fallback to rules-only mode if keys absent)
    # Provider options: "auto", "gemini", "anthropic", "none"
    llm_provider: str = os.getenv("FLOWDESK_LLM_PROVIDER", "auto").lower()
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")

    # Triage & Pattern Detection thresholds
    confidence_threshold: float = float(os.getenv("FLOWDESK_CONFIDENCE_THRESHOLD", "0.75"))
    incident_min_tickets: int = int(os.getenv("FLOWDESK_INCIDENT_MIN_TICKETS", "3"))
    incident_window_hours: int = int(os.getenv("FLOWDESK_INCIDENT_WINDOW_HOURS", "48"))

    # Known issues directory
    kb_dir: Path = BASE_DIR / "docs" / "known_issues"
    data_dir: Path = BASE_DIR / "data"


settings = Settings()

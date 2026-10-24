"""Ticket ingestion service for CSV and JSON data."""

import csv
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from flowdesk.db import Ticket


class TicketIngestModel(BaseModel):
    id: str = Field(..., min_length=1)
    created_at: datetime
    channel: str = Field(default="email")
    platform: str
    app_version: str
    os_version: str
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    plan_tier: str = Field(default="free")

    # Optional fields for pre-labeled datasets
    category: str | None = None
    severity: str | None = None
    sentiment: str | None = None
    confidence: float | None = None
    triage_reason: str | None = None
    triage_method: str | None = None
    matched_kb: str | None = None

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_datetime(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            value = value.strip()
            # Try ISO formats first
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
            # Try common variations
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
            ):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        raise ValueError(f"Cannot parse datetime from: {value}")

    @field_validator("platform", mode="before")
    @classmethod
    def clean_platform(cls, value: Any) -> str:
        if not value:
            return "unknown"
        val = str(value).strip().lower()
        if "mac" in val:
            return "macos"
        if "win" in val:
            return "windows"
        if "ios" in val or "iphone" in val or "ipad" in val:
            return "ios"
        if "android" in val:
            return "android"
        if "web" in val or "chrome" in val:
            return "web"
        return val

    @field_validator("plan_tier", mode="before")
    @classmethod
    def clean_plan_tier(cls, value: Any) -> str:
        if not value:
            return "free"
        val = str(value).strip().lower()
        if val in {"enterprise", "business"}:
            return "enterprise"
        if val in {"pro", "paid", "premium"}:
            return "pro"
        return "free"


def parse_csv_stream(content: str | io.StringIO) -> list[dict[str, Any]]:
    """Parse CSV content into a list of row dictionaries."""
    if isinstance(content, str):
        content = io.StringIO(content.strip())
    reader = csv.DictReader(content)
    rows = []
    for row in reader:
        # Strip keys and values
        clean_row = {
            (k.strip() if k else ""): (v.strip() if isinstance(v, str) else v)
            for k, v in row.items()
            if k is not None
        }
        rows.append(clean_row)
    return rows


def parse_json_stream(content: str | bytes) -> list[dict[str, Any]]:
    """Parse JSON content into a list of dictionaries."""
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    data = json.loads(content)
    if isinstance(data, dict) and "tickets" in data:
        return data["tickets"]
    if isinstance(data, list):
        return data
    raise ValueError("JSON must be a list of ticket objects or have a top-level 'tickets' key.")


def ingest_tickets(
    records: list[dict[str, Any]],
    db: Session,
    overwrite_existing: bool = True,
) -> dict[str, Any]:
    """Validate and insert ticket records into the database.

    Returns stats dict: {imported: int, skipped: int, errors: list[str]}.
    """
    imported_count = 0
    skipped_count = 0
    errors: list[str] = []

    for idx, raw in enumerate(records):
        try:
            model = TicketIngestModel.model_validate(raw)
            existing = db.get(Ticket, model.id)
            if existing:
                if overwrite_existing:
                    for field, val in model.model_dump(exclude_unset=True).items():
                        setattr(existing, field, val)
                    imported_count += 1
                else:
                    skipped_count += 1
                continue

            ticket = Ticket(**model.model_dump())
            db.add(ticket)
            imported_count += 1
        except Exception as e:
            errors.append(f"Row {idx + 1} (ID: {raw.get('id', 'unknown')}): {e}")

    db.commit()
    return {
        "imported": imported_count,
        "skipped": skipped_count,
        "errors": errors,
        "total": len(records),
    }


def ingest_from_file(file_path: str | Path, db: Session) -> dict[str, Any]:
    """Ingest tickets directly from a CSV or JSON file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    if suffix == ".csv":
        records = parse_csv_stream(text)
    elif suffix == ".json":
        records = parse_json_stream(text)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Expected .csv or .json")

    return ingest_tickets(records, db)

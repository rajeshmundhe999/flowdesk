"""Unit tests for ticket ingestion."""

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from flowdesk.db import Base, Ticket
from flowdesk.ingestion import ingest_from_file, ingest_tickets, parse_json_stream


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_ingest_sample_tickets_csv(test_db):
    sample_csv = Path(__file__).resolve().parent.parent / "data" / "sample_tickets.csv"
    assert sample_csv.exists(), "Sample CSV must exist"

    result = ingest_from_file(sample_csv, test_db)
    assert result["imported"] == 60, f"Expected 60 tickets, got {result['imported']}"
    assert result["errors"] == []

    # Check that database contains 60 records
    count = test_db.query(Ticket).count()
    assert count == 60

    # Verify a known sample record
    tck_1001 = test_db.get(Ticket, "TCK-1001")
    assert tck_1001 is not None
    assert tck_1001.platform == "windows"
    assert tck_1001.app_version == "1.4.2"
    assert tck_1001.plan_tier == "enterprise"
    assert "Zscaler VPN" in tck_1001.body


def test_ingest_json_stream(test_db):
    payload = json.dumps(
        [
            {
                "id": "TCK-TEST-1",
                "created_at": "2026-10-24T10:00:00Z",
                "channel": "chat",
                "platform": "macOS 14.5",
                "app_version": "1.4.3",
                "os_version": "macOS Sonoma",
                "subject": "Audio lag",
                "body": "Audio lag on start",
                "plan_tier": "pro",
            }
        ]
    )
    records = parse_json_stream(payload)
    result = ingest_tickets(records, test_db)
    assert result["imported"] == 1
    assert result["errors"] == []

    ticket = test_db.get(Ticket, "TCK-TEST-1")
    assert ticket is not None
    assert ticket.platform == "macos"
    assert ticket.plan_tier == "pro"


def test_ingest_handles_malformed_records(test_db):
    records = [
        {
            "id": "VALID-1",
            "created_at": "2026-10-24T12:00:00Z",
            "channel": "email",
            "platform": "windows",
            "app_version": "1.0",
            "os_version": "Win11",
            "subject": "Valid Subject",
            "body": "Valid body text",
            "plan_tier": "free",
        },
        {
            # Missing ID and created_at
            "subject": "Invalid Subject",
            "body": "No ID here",
        },
    ]

    result = ingest_tickets(records, test_db)
    assert result["imported"] == 1
    assert len(result["errors"]) == 1
    assert "Row 2" in result["errors"][0]

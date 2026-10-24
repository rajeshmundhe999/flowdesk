"""Unit tests for pattern detection and ticket clustering."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from flowdesk.clustering import cluster_tickets, run_pattern_detection
from flowdesk.db import Base, Incident, Ticket
from flowdesk.ingestion import ingest_from_file


@pytest.fixture
def memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def create_mock_ticket(
    tid: str,
    created_at: datetime,
    platform: str,
    app_version: str,
    subject: str,
    body: str,
    category: str = "hotkeys",
    severity: str = "P2",
) -> Ticket:
    return Ticket(
        id=tid,
        created_at=created_at,
        platform=platform,
        app_version=app_version,
        os_version="macOS 14.5",
        subject=subject,
        body=body,
        category=category,
        severity=severity,
    )


def test_cluster_flags_three_or_more_tickets():
    base_time = datetime(2026, 10, 22, 8, 0, 0)
    tickets = [
        create_mock_ticket(
            f"TCK-{i}",
            base_time + timedelta(minutes=i * 20),
            "macos",
            "1.4.3",
            "Hotkey blocked in terminal",
            "Hotkey fails because macOS Secure Keyboard Entry is active.",
        )
        for i in range(4)
    ]

    incidents = cluster_tickets(tickets, min_tickets=3, window_hours=24)
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.ticket_count == 4
    assert inc.signature == "Secure Keyboard Entry"
    assert "Secure Keyboard Entry" in inc.title
    assert "macos" in inc.affected_platforms


def test_cluster_ignores_under_threshold():
    base_time = datetime(2026, 10, 22, 8, 0, 0)
    tickets = [
        create_mock_ticket(
            f"TCK-{i}",
            base_time + timedelta(minutes=i * 15),
            "macos",
            "1.4.3",
            "Hotkey blocked in terminal",
            "Hotkey fails because macOS Secure Keyboard Entry is active.",
        )
        for i in range(2)  # Only 2 tickets
    ]

    incidents = cluster_tickets(tickets, min_tickets=3, window_hours=24)
    assert len(incidents) == 0


def test_pattern_detection_on_sample_data(memory_db):
    sample_csv = Path(__file__).resolve().parent.parent / "data" / "sample_tickets.csv"
    ingest_from_file(sample_csv, memory_db)

    incidents = run_pattern_detection(memory_db, min_tickets=3, window_hours=48)
    assert len(incidents) >= 4, f"Expected multiple incidents detected, got {len(incidents)}"

    # Check that incidents are saved in the DB
    db_incidents = memory_db.query(Incident).all()
    assert len(db_incidents) == len(incidents)

    # Check that tickets got their cluster_id set
    clustered_tickets = memory_db.query(Ticket).filter(Ticket.cluster_id.isnot(None)).all()
    assert len(clustered_tickets) >= 12

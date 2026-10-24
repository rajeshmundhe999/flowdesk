"""Integration tests for FlowDesk FastAPI endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from flowdesk.db import Base, get_db
from flowdesk.ingestion import ingest_from_file
from flowdesk.main import app


@pytest.fixture(scope="module")
def test_app_client(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("flowdesk_test_db")
    db_file = tmp_dir / "test_api.db"
    db_url = f"sqlite:///{db_file}"

    test_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Pre-seed with sample tickets
    sample_csv = Path(__file__).resolve().parent.parent / "data" / "sample_tickets.csv"
    with TestingSessionLocal() as session:
        ingest_from_file(sample_csv, session)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_get_dashboard(test_app_client):
    response = test_app_client.get("/")
    assert response.status_code == 200


def test_get_stats(test_app_client):
    response = test_app_client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_tickets" in data
    assert "severity_breakdown" in data
    assert "incidents_count" in data


def test_list_tickets(test_app_client):
    response = test_app_client.get("/api/tickets")
    assert response.status_code == 200
    tickets = response.json()
    assert isinstance(tickets, list)
    assert len(tickets) > 0


def test_get_incidents(test_app_client):
    # Trigger cluster detection first
    test_app_client.post("/api/triage/batch")
    test_app_client.post("/api/incidents/detect")

    response = test_app_client.get("/api/incidents")
    assert response.status_code == 200
    incidents = response.json()
    assert isinstance(incidents, list)
    assert len(incidents) > 0


def test_get_kb_articles(test_app_client):
    response = test_app_client.get("/api/kb")
    assert response.status_code == 200
    articles = response.json()
    assert len(articles) == 11
    titles = [a["id"] for a in articles]
    assert "net_connection_lost_vpn" in titles


def test_get_ticket_reply(test_app_client):
    tickets = test_app_client.get("/api/tickets").json()
    ticket_id = tickets[0]["id"]

    response = test_app_client.post(f"/api/tickets/{ticket_id}/reply")
    assert response.status_code == 200
    data = response.json()
    assert data["requires_human_review"] is True
    assert data["anti_promise_audit_passed"] is True
    assert "Recommended Steps to Fix" in data["draft_text"]


def test_get_ticket_report(test_app_client):
    tickets = test_app_client.get("/api/tickets").json()
    ticket_id = tickets[0]["id"]

    response = test_app_client.get(f"/api/tickets/{ticket_id}/report")
    assert response.status_code == 200
    data = response.json()
    assert "# [BUG]" in data["markdown_report"]


def test_create_and_triage_custom_ticket(test_app_client):
    payload = {
        "subject": "Audio stuttering on Bluetooth Sony XM4",
        "body": (
            "Whenever I dictate, the audio input switches to Hands-Free AG Audio mode "
            "and sounds terrible."
        ),
        "platform": "windows",
        "app_version": "1.4.3",
        "os_version": "Windows 11",
        "plan_tier": "enterprise",
        "channel": "chat",
    }
    response = test_app_client.post("/api/tickets", json=payload)
    assert response.status_code == 200
    ticket = response.json()
    assert ticket["id"].startswith("TCK-")
    assert ticket["category"] == "audio/mic"
    assert ticket["severity"] in {"P1", "P2"}
    assert ticket["triage_method"] == "rules"
    assert ticket["triaged_at"] is not None


def test_get_evaluation(test_app_client):
    response = test_app_client.get("/api/evaluate")
    assert response.status_code == 200
    data = response.json()
    assert data["category_accuracy"] > 80.0
    assert "confusion_matrix" in data

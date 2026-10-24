"""FlowDesk FastAPI application server."""

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from diagnose import run_diagnostics
from evaluate import evaluate_dataset, load_labeled_dataset
from flowdesk.bug_reports import (
    generate_bug_report_from_incident,
    generate_bug_report_from_ticket,
)
from flowdesk.clustering import cluster_tickets, run_pattern_detection
from flowdesk.config import settings
from flowdesk.db import Incident, Ticket, get_db, init_db
from flowdesk.ingestion import ingest_from_file
from flowdesk.kb import load_all_kb_articles
from flowdesk.replies import draft_customer_reply
from flowdesk.triage.engine import triage_and_update_ticket

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema
    init_db()

    # Seed sample data on first launch if DB is empty
    from flowdesk.db import SessionLocal

    with SessionLocal() as db:
        if db.query(Ticket).count() == 0:
            sample_csv = settings.data_dir / "sample_tickets.csv"
            if sample_csv.exists():
                ingest_from_file(sample_csv, db)
                # Auto triage and run cluster detection on initial seed
                tickets = db.query(Ticket).all()
                for t in tickets:
                    triage_and_update_ticket(t)
                db.commit()
                run_pattern_detection(db)

    yield


app = FastAPI(
    title="FlowDesk Support Engineering Toolkit",
    version="0.1.0",
    description="Support Engineering Toolkit for Voice-Dictation SaaS products",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_dashboard():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "FlowDesk API is running. Static UI not found."}


@app.get("/api/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    total = db.query(Ticket).count()
    p0 = db.query(Ticket).filter(Ticket.severity == "P0").count()
    p1 = db.query(Ticket).filter(Ticket.severity == "P1").count()
    p2 = db.query(Ticket).filter(Ticket.severity == "P2").count()
    p3 = db.query(Ticket).filter(Ticket.severity == "P3").count()
    incidents_count = db.query(Incident).count()
    triaged_count = db.query(Ticket).filter(Ticket.category.isnot(None)).count()

    return {
        "total_tickets": total,
        "triaged_tickets": triaged_count,
        "incidents_count": incidents_count,
        "severity_breakdown": {"P0": p0, "P1": p1, "P2": p2, "P3": p3},
    }


@app.get("/api/tickets")
def list_tickets(
    category: str | None = Query(None),
    severity: str | None = Query(None),
    platform: str | None = Query(None),
    plan_tier: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(Ticket).order_by(Ticket.created_at.desc())

    if category:
        query = query.filter(Ticket.category == category)
    if severity:
        query = query.filter(Ticket.severity == severity)
    if platform:
        query = query.filter(Ticket.platform == platform)
    if plan_tier:
        query = query.filter(Ticket.plan_tier == plan_tier)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            Ticket.subject.ilike(search_filter) | Ticket.body.ilike(search_filter)
        )

    tickets = query.limit(limit).all()
    return [t.to_dict() for t in tickets]


class CreateTicketRequest(BaseModel):
    subject: str = Field(..., min_length=2)
    body: str = Field(..., min_length=2)
    platform: str = Field(default="windows")
    app_version: str = Field(default="1.4.3")
    os_version: str = Field(default="Windows 11")
    plan_tier: str = Field(default="pro")
    channel: str = Field(default="in-app")


@app.post("/api/tickets")
def create_ticket(req: CreateTicketRequest, db: Session = Depends(get_db)):
    """Create a new customer ticket, run real-time triage, and update pattern detection."""
    ticket_id = f"TCK-{uuid.uuid4().hex[:6].upper()}"

    ticket = Ticket(
        id=ticket_id,
        created_at=datetime.now(UTC),
        channel=req.channel,
        platform=req.platform.lower().strip(),
        app_version=req.app_version.strip(),
        os_version=req.os_version.strip(),
        subject=req.subject.strip(),
        body=req.body.strip(),
        plan_tier=req.plan_tier.lower().strip(),
    )

    # Real-time automated triage
    triage_and_update_ticket(ticket)
    db.add(ticket)
    db.commit()

    # Re-evaluate incident patterns
    run_pattern_detection(db)

    db.refresh(ticket)
    return ticket.to_dict()


@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket.to_dict()


@app.post("/api/tickets/seed")
def seed_sample_data(db: Session = Depends(get_db)):
    sample_csv = settings.data_dir / "sample_tickets.csv"
    if not sample_csv.exists():
        raise HTTPException(status_code=404, detail="sample_tickets.csv not found")

    res = ingest_from_file(sample_csv, db)
    # Triage and cluster
    tickets = db.query(Ticket).all()
    for t in tickets:
        triage_and_update_ticket(t)
    db.commit()
    incidents = run_pattern_detection(db)

    return {
        "ingested": res["imported"],
        "incidents_detected": len(incidents),
        "total_tickets": db.query(Ticket).count(),
    }


@app.post("/api/triage/batch")
def batch_triage(db: Session = Depends(get_db)):
    tickets = db.query(Ticket).all()
    count = 0
    for t in tickets:
        triage_and_update_ticket(t)
        count += 1
    db.commit()
    incidents = run_pattern_detection(db)
    return {"triaged": count, "incidents_detected": len(incidents)}


@app.post("/api/tickets/{ticket_id}/triage")
def triage_single_ticket(ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    updated = triage_and_update_ticket(ticket)
    db.commit()
    return updated.to_dict()


@app.get("/api/incidents")
def list_incidents(db: Session = Depends(get_db)):
    incidents = db.query(Incident).order_by(Incident.ticket_count.desc()).all()
    return [inc.to_dict() for inc in incidents]


@app.post("/api/incidents/detect")
def trigger_incident_detection(db: Session = Depends(get_db)):
    incidents = run_pattern_detection(db)
    return {"incidents_detected": len(incidents), "incidents": [inc.to_dict() for inc in incidents]}


@app.get("/api/incidents/{incident_id}/report")
def get_incident_bug_report(incident_id: str, db: Session = Depends(get_db)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    tickets = db.query(Ticket).filter(Ticket.cluster_id == incident.id).all()
    all_tickets = db.query(Ticket).all()
    summaries = cluster_tickets(all_tickets)

    target_summary = next((s for s in summaries if s.id == incident.id), None)
    if not target_summary:
        from flowdesk.clustering import build_cluster_summary, generate_cluster_key

        target_summary = build_cluster_summary(
            generate_cluster_key(tickets[0]),
            tickets,
        )

    report_markdown = generate_bug_report_from_incident(target_summary, tickets)
    return {
        "incident_id": incident.id,
        "title": incident.title,
        "markdown_report": report_markdown,
    }


@app.get("/api/tickets/{ticket_id}/report")
def get_ticket_bug_report(ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    related: list[Ticket] = []
    if ticket.cluster_id:
        related = (
            db.query(Ticket)
            .filter(Ticket.cluster_id == ticket.cluster_id, Ticket.id != ticket.id)
            .all()
        )

    report_markdown = generate_bug_report_from_ticket(ticket, related)
    return {
        "ticket_id": ticket.id,
        "subject": ticket.subject,
        "markdown_report": report_markdown,
    }


@app.post("/api/tickets/{ticket_id}/reply")
def generate_ticket_reply(ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    draft = draft_customer_reply(ticket)
    return draft


@app.get("/api/kb")
def get_knowledge_base():
    articles = load_all_kb_articles()
    return [
        {
            "id": a.id,
            "title": a.title,
            "filename": a.filename,
            "symptom": a.symptom,
            "fix": a.fix,
            "data_safety": a.data_safety,
            "escalation_criteria": a.escalation_criteria,
        }
        for a in articles
    ]


@app.get("/api/diagnose")
def run_diagnostics_api():
    config_file = settings.kb_dir.parent.parent / "diagnose_config.json"
    results = run_diagnostics(config_file)
    return [r.to_dict() for r in results]


@app.get("/api/evaluate")
def run_evaluation_api():
    dataset_file = settings.data_dir / "labeled_tickets.csv"
    rows = load_labeled_dataset(dataset_file)
    return evaluate_dataset(rows)

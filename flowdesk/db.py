"""Database models and session management for FlowDesk."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from flowdesk.config import settings


class Base(DeclarativeBase):
    pass


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String(64), primary_key=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    channel = Column(String(32), nullable=False, default="email")  # email, chat, in-app, web
    platform = Column(String(32), nullable=False)  # macos, windows, ios, android, web
    app_version = Column(String(32), nullable=False)
    os_version = Column(String(64), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    plan_tier = Column(String(32), nullable=False, default="free")  # free, pro, enterprise

    # Triage metadata
    category = Column(String(64), nullable=True)
    severity = Column(String(8), nullable=True)  # P0, P1, P2, P3
    sentiment = Column(String(32), nullable=True)  # frustrated, neutral, satisfied
    confidence = Column(Float, nullable=True)
    triage_reason = Column(Text, nullable=True)
    triage_method = Column(String(32), nullable=True)  # rules, llm, manual
    matched_kb = Column(String(128), nullable=True)
    cluster_id = Column(String(64), nullable=True)
    triaged_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_platform_app_version", "platform", "app_version"),
        Index("idx_category_severity", "category", "severity"),
        Index("idx_cluster", "cluster_id"),
        Index("idx_created_at", "created_at"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "channel": self.channel,
            "platform": self.platform,
            "app_version": self.app_version,
            "os_version": self.os_version,
            "subject": self.subject,
            "body": self.body,
            "plan_tier": self.plan_tier,
            "category": self.category,
            "severity": self.severity,
            "sentiment": self.sentiment,
            "confidence": self.confidence,
            "triage_reason": self.triage_reason,
            "triage_method": self.triage_method,
            "matched_kb": self.matched_kb,
            "cluster_id": self.cluster_id,
            "triaged_at": self.triaged_at.isoformat() if self.triaged_at else None,
        }


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(64), primary_key=True)
    title = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False)
    severity = Column(String(8), nullable=False)
    ticket_count = Column(Integer, nullable=False, default=0)
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    affected_platforms = Column(String(255), nullable=False)
    affected_versions = Column(String(255), nullable=False)
    signature = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "severity": self.severity,
            "ticket_count": self.ticket_count,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "affected_platforms": self.affected_platforms.split(",")
            if self.affected_platforms
            else [],
            "affected_versions": self.affected_versions.split(",")
            if self.affected_versions
            else [],
            "signature": self.signature,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def get_engine(db_url: str | None = None):
    url = db_url or settings.database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(db_engine=None) -> None:
    target_engine = db_engine or engine
    Base.metadata.create_all(bind=target_engine)


@contextmanager
def get_db_context(session_factory=None) -> Generator[Session, None, None]:
    factory = session_factory or SessionLocal
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

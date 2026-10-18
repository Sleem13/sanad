"""Pilot DB (SQLite for dev; same models target PostgreSQL). Page content is stored as versioned, immutable JSON rows,
NOT as one row per token. Originals live on disk, content-addressed, read-only."""
from __future__ import annotations
import hashlib, json, uuid
from datetime import datetime, timezone
from sqlalchemy import (create_engine, String, Integer, Text, DateTime, ForeignKey, UniqueConstraint, JSON, Boolean, event)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session


def now() -> datetime:
    return datetime.now(timezone.utc)


def uid() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class UnderstandingRun(Base):
    __tablename__ = "understanding_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    page_id: Mapped[str] = mapped_column(ForeignKey("pages.id"), index=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("page_versions.id"), index=True)
    model: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="running")
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SourceArtifact(Base):
    __tablename__ = "source_artifacts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    org_scope: Mapped[str] = mapped_column(String, index=True)
    sha256: Mapped[str] = mapped_column(String, index=True)
    original_filename: Mapped[str] = mapped_column(String)      # untrusted label only; never used as a path
    media_type: Mapped[str] = mapped_column(String, default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="accepted")   # accepted | quarantined
    quarantine_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    is_synthetic_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("org_scope", "sha256", name="uq_artifact_org_sha"),)


class Document(Base):
    """Logical document. File-level duplicates are NOT merged into one logical document automatically."""
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("source_artifacts.id"))
    org_scope: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, default="ingested")  # ingested|processing|processed|partial_failure|blocked|failed|in_review|approved
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Page(Base):
    __tablename__ = "pages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    page_no: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    rotation: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="pending")   # pending|processed|failed|in_review|approved
    __table_args__ = (UniqueConstraint("document_id", "page_no"),)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String, unique=True)
    engine_id: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="queued")  # queued|running|succeeded|partial_failure|failed|blocked|cancelled
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)


class ProcessingRun(Base):
    __tablename__ = "processing_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    page_id: Mapped[str] = mapped_column(ForeignKey("pages.id"), index=True)
    engine_id: Mapped[str] = mapped_column(String)
    engine_version: Mapped[str] = mapped_column(String)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String)         # succeeded | failed | failed_validation
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_output_path: Mapped[str | None] = mapped_column(String, nullable=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PageVersion(Base):
    """Immutable. kind: raw (parsed engine output) | draft (human edit, not approved) | approved."""
    __tablename__ = "page_versions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    page_id: Mapped[str] = mapped_column(ForeignKey("pages.id"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String)
    parent_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    content: Mapped[dict] = mapped_column(JSON)
    author: Mapped[str] = mapped_column(String)
    run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("page_id", "version_no", name="uq_page_version_no"),
                      UniqueConstraint("run_id", name="uq_version_run"))   # idempotent effect per run


class ReviewTask(Base):
    __tablename__ = "review_tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    page_id: Mapped[str] = mapped_column(ForeignKey("pages.id"), index=True, unique=True)
    assignee: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="open")   # open|in_progress|approved|escalated|reopened
    escalation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Correction(Base):
    __tablename__ = "corrections"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    page_id: Mapped[str] = mapped_column(String, index=True)
    version_id: Mapped[str] = mapped_column(String)
    region_id: Mapped[str] = mapped_column(String)
    old_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    author: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    page_id: Mapped[str] = mapped_column(String, index=True)
    version_id: Mapped[str] = mapped_column(String)
    approved_by: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DeliveryRecord(Base):
    __tablename__ = "delivery_records"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(String, index=True)
    schema_name: Mapped[str] = mapped_column(String)
    schema_version: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)          # delivered | rejected
    errors: Mapped[list] = mapped_column(JSON, default=list)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_version_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_by: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditEvent(Base):
    """Append-only, hash-chained (tamper-evident, not tamper-proof: anchor the head hash externally in production)."""
    __tablename__ = "audit_events"
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    actor: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    object_type: Mapped[str] = mapped_column(String)
    object_id: Mapped[str] = mapped_column(String)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String)
    hash: Mapped[str] = mapped_column(String)


def audit(s: Session, actor: str, action: str, otype: str, oid: str, detail: dict | None = None) -> None:
    last = s.query(AuditEvent).order_by(AuditEvent.seq.desc()).first()
    prev = last.hash if last else "0" * 64
    ts = now()
    body = json.dumps({"ts": ts.isoformat(), "actor": actor, "action": action, "ot": otype, "oid": oid,
                       "detail": detail or {}}, sort_keys=True, ensure_ascii=False)
    h = hashlib.sha256((prev + body).encode()).hexdigest()
    s.add(AuditEvent(ts=ts, actor=actor, action=action, object_type=otype, object_id=oid,
                     detail=detail or {}, prev_hash=prev, hash=h))
    s.flush()


def verify_audit_chain(s: Session) -> tuple[bool, int | None]:
    prev = "0" * 64
    for e in s.query(AuditEvent).order_by(AuditEvent.seq):
        body = json.dumps({"ts": e.ts.replace(tzinfo=timezone.utc).isoformat() if e.ts.tzinfo is None else e.ts.isoformat(),
                           "actor": e.actor, "action": e.action, "ot": e.object_type, "oid": e.object_id,
                           "detail": e.detail}, sort_keys=True, ensure_ascii=False)
        if e.prev_hash != prev or hashlib.sha256((prev + body).encode()).hexdigest() != e.hash:
            return False, e.seq
        prev = e.hash
    return True, None


def make_session_factory(url: str):
    eng = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {})
    if url.startswith("sqlite"):
        @event.listens_for(eng, "connect")
        def _pragma(dbapi, _):
            dbapi.execute("PRAGMA foreign_keys=ON")
        with eng.connect() as connection:
            connection.exec_driver_sql("PRAGMA journal_mode=WAL")
    Base.metadata.create_all(eng)
    return sessionmaker(eng, expire_on_commit=False)

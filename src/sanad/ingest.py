"""Safe ingestion: size/type/magic-byte/decompression-bomb checks, content-addressed read-only original, quarantine on failure."""
from __future__ import annotations
import hashlib, io, os, stat
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session
from .config import Settings
from .db import SourceArtifact, Document, Page, Job, audit

ALLOWED = {"PNG": "image/png", "JPEG": "image/jpeg", "TIFF": "image/tiff"}   # PDF rendering: pending (see backlog)


class IngestRejected(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _store(base: Path, sub: str, sha: str, data: bytes) -> Path:
    d = base / sub / sha[:2]
    d.mkdir(parents=True, exist_ok=True)
    p = d / sha                       # filename derived from hash only -> no path traversal from user input
    if not p.exists():
        p.write_bytes(data)
        os.chmod(p, stat.S_IRUSR | stat.S_IRGRP)       # originals are read-only
    return p


def ingest_bytes(s: Session, cfg: Settings, *, data: bytes, filename: str, org_scope: str, actor: str,
                 demo: bool = False) -> tuple[SourceArtifact, Document | None, bool]:
    """Returns (artifact, document|None, was_duplicate). Duplicate = same bytes within the same org scope (file-level only)."""
    sha = hashlib.sha256(data).hexdigest()
    existing = s.query(SourceArtifact).filter_by(org_scope=org_scope, sha256=sha).first()
    if existing:
        audit(s, actor, "ingest.duplicate_file", "source_artifact", existing.id, {"sha256": sha})
        doc = s.query(Document).filter_by(artifact_id=existing.id).first() if existing.status == "accepted" else None
        return existing, doc, True

    reason, fmt, size = None, None, None
    if len(data) == 0:
        reason = "empty_file"
    elif len(data) > cfg.max_upload_bytes:
        reason = "file_too_large"
    else:
        Image.MAX_IMAGE_PIXELS = cfg.max_image_pixels
        try:
            with Image.open(io.BytesIO(data)) as im:
                fmt, size = im.format, im.size
                if fmt not in ALLOWED:
                    reason = f"unsupported_format:{fmt}"
                elif size[0] * size[1] > cfg.max_image_pixels:
                    reason = "too_many_pixels"
                else:
                    im.verify()           # structural check
            if reason is None:
                with Image.open(io.BytesIO(data)) as im2:
                    im2.load()            # full decode catches truncated data
        except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning, OSError, SyntaxError, ValueError) as e:
            reason = f"corrupt_or_unreadable:{type(e).__name__}"

    if reason:
        p = _store(cfg.data_dir, "quarantine", sha, data) if data else Path("")
        art = SourceArtifact(org_scope=org_scope, sha256=sha, original_filename=os.path.basename(filename)[:200],
                             size_bytes=len(data), storage_path=str(p), status="quarantined",
                             quarantine_reason=reason, created_by=actor, is_synthetic_demo=demo)
        s.add(art); s.flush()
        audit(s, actor, "ingest.quarantined", "source_artifact", art.id, {"reason": reason, "sha256": sha})
        return art, None, False

    p = _store(cfg.data_dir, "originals", sha, data)
    art = SourceArtifact(org_scope=org_scope, sha256=sha, original_filename=os.path.basename(filename)[:200],
                         media_type=ALLOWED[fmt], size_bytes=len(data), storage_path=str(p),
                         created_by=actor, is_synthetic_demo=demo)
    s.add(art); s.flush()
    doc = Document(artifact_id=art.id, org_scope=org_scope, page_count=1)
    s.add(doc); s.flush()
    s.add(Page(document_id=doc.id, page_no=1, width=size[0], height=size[1]))
    s.flush()
    audit(s, actor, "ingest.accepted", "document", doc.id, {"artifact_id": art.id, "sha256": sha})
    enqueue(s, cfg, doc, actor)
    return art, doc, False


def enqueue(s: Session, cfg: Settings, doc: Document, actor: str, engine_id: str | None = None, tag: str = "initial") -> Job:
    engine_id = engine_id or cfg.engine
    key = f"{doc.id}:{engine_id}:{tag}"
    job = s.query(Job).filter_by(idempotency_key=key).first()
    if job:
        return job
    job = Job(document_id=doc.id, idempotency_key=key, engine_id=engine_id, max_attempts=cfg.job_max_attempts)
    s.add(job); s.flush()
    audit(s, actor, "job.enqueued", "job", job.id, {"engine": engine_id})
    return job

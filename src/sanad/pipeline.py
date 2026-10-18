"""Worker: at-least-once job execution with idempotent effects (unique run_id per page version), bounded retries with
exponential backoff, lease-based crash recovery, per-page failure isolation, strict output validation."""
from __future__ import annotations
import json, traceback
from datetime import timedelta
from pathlib import Path
from pydantic import ValidationError
from sqlalchemy.orm import Session
from .canonical import CanonicalPage, Region, RegionStatus
from .config import Settings
from .db import (Job, Document, Page, ProcessingRun, PageVersion, ReviewTask, SourceArtifact, audit, now)
from .engines.base import EngineUnavailable

SYSTEM = "system.worker"


def claim_next(s: Session, cfg: Settings) -> Job | None:
    t = now()
    q = s.query(Job).filter(Job.engine_id == cfg.engine).filter(
        ((Job.status == "queued") & (Job.next_attempt_at <= t)) |
        ((Job.status == "running") & (Job.locked_until < t)))          # crashed worker: lease expired
    job = q.order_by(Job.next_attempt_at).first()
    if not job:
        return None
    if job.status == "running":
        audit(s, SYSTEM, "job.lease_expired_reclaimed", "job", job.id)
    job.status, job.attempts = "running", job.attempts + 1
    job.locked_until = t + timedelta(seconds=cfg.job_lease_seconds)
    s.flush()
    return job


def _page_done(s: Session, job: Job, page: Page) -> bool:
    return s.query(ProcessingRun).filter_by(job_id=job.id, page_id=page.id, status="succeeded").first() is not None


def process_job(s: Session, cfg: Settings, engine, job: Job) -> str:
    doc = s.get(Document, job.document_id)
    art = s.get(SourceArtifact, doc.artifact_id)
    doc.status = "processing"
    pages = s.query(Page).filter_by(document_id=doc.id).order_by(Page.page_no).all()
    failures = 0
    for page in pages:
        if _page_done(s, job, page):                      # idempotent re-delivery: skip finished pages
            continue
        s.refresh(job)
        if job.cancel_requested:
            job.status = "cancelled"; doc.status = "ingested"
            audit(s, SYSTEM, "job.cancelled", "job", job.id)
            return "cancelled"
        run = ProcessingRun(job_id=job.id, page_id=page.id, engine_id=engine.engine_id,
                            engine_version=engine.version(), config=engine.config(),
                            status="running", is_mock=engine.is_mock)
        s.add(run); s.flush()
        # Native inference can take minutes. Persist provenance and release the
        # database writer lock so uploads, review and image audit reads keep working.
        s.commit()
        try:
            kwargs = {"page_no": page.page_no}
            result = engine.recognize(art.storage_path, page.width, page.height, **kwargs)
        except EngineUnavailable as e:
            run.status, run.error, run.finished_at = "failed", f"blocked: {e}", now()
            job.status, job.last_error = "blocked", str(e)
            job.attempts -= 1                              # blocked work does not consume retries
            doc.status = "blocked"
            audit(s, SYSTEM, "job.blocked", "job", job.id, {"reason": str(e)})
            return "blocked"
        except Exception as e:                             # isolate per-page failure
            failures += 1
            page.status = "failed"
            run.status, run.error, run.finished_at = "failed", f"{type(e).__name__}: {e}", now()
            audit(s, SYSTEM, "page.failed", "page", page.id, {"error": run.error})
            continue

        raw_path = Path(cfg.data_dir) / "raw_outputs" / f"{run.id}.json"
        if engine.engine_id == "paddleocr_vl":
            baseline = s.query(PageVersion).filter_by(page_id=page.id, author="engine:paddleocr_arabic", is_mock=False).order_by(PageVersion.version_no.desc()).first()
            if baseline and baseline.content.get("source_sha256") == art.sha256:
                from .engines.comparison import attach_comparison
                attach_comparison(result.regions, baseline.content["regions"], f"paddleocr_arabic:v{baseline.version_no}")
        raw_path.write_text(json.dumps(result.raw, ensure_ascii=False, default=str), encoding="utf-8")
        run.raw_output_path = str(raw_path)
        try:
            regions = []
            for i, r in enumerate(result.regions):
                if r.bbox is None:
                    raise ValueError(f"region {i}: missing source linkage (bbox)")
                st = RegionStatus.recognized if (r.text or "").strip() else RegionStatus.not_processed
                flags = ["non_text_region"] if r.label in {"seal", "signature", "stamp", "image", "figure"} and not r.text else []
                flags.extend(r.extra.get("flags", []))
                if st == RegionStatus.recognized and r.extra.get("requires_review"):
                    st = RegionStatus.requires_review
                regions.append(Region(region_id=f"r{i+1}", label=r.label, bbox=r.bbox, polygon=r.polygon,
                                      text=r.text if (r.text or "").strip() else None, status=st,
                                      reading_order=r.reading_order, engine_score=r.engine_score,
                                      engine_score_kind=r.engine_score_kind, flags=flags,
                                      alternatives=r.extra.get("alternatives", []),
                                      alternative_sources=r.extra.get("alternative_sources", []), cells=r.extra.get("cells")))
            cp = CanonicalPage(page_id=page.id, page_no=page.page_no, width=page.width, height=page.height,
                               rotation=page.rotation, source_sha256=art.sha256, regions=regions)
        except (ValidationError, ValueError) as e:
            failures += 1
            page.status = "failed"
            run.status, run.error, run.finished_at = "failed_validation", str(e)[:2000], now()
            audit(s, SYSTEM, "page.validation_failed", "page", page.id, {"error": run.error[:500]})
            continue

        try:
            with s.begin_nested():
                previous = s.query(PageVersion).filter_by(page_id=page.id).order_by(PageVersion.version_no.desc()).first()
                if previous and previous.kind == "approved":
                    raise ValueError("approved page must be reopened before reprocessing")
                s.add(PageVersion(page_id=page.id, version_no=previous.version_no + 1 if previous else 1,
                                  kind="raw", content=cp.model_dump(mode="json"),
                                  author=f"engine:{engine.engine_id}", run_id=run.id, is_mock=engine.is_mock))
                s.flush()
        except Exception as e:
            failures += 1
            page.status = "failed"
            run.status, run.error, run.finished_at = "failed_validation", str(e)[:2000], now()
            continue
        if not s.query(ReviewTask).filter_by(page_id=page.id).first():
            s.add(ReviewTask(page_id=page.id))
        page.status = "in_review"
        run.status, run.finished_at = "succeeded", now()
        audit(s, SYSTEM, "page.processed", "page", page.id, {"run": run.id, "mock": engine.is_mock})

    if failures == 0:
        job.status, job.locked_until, doc.status = "succeeded", None, "in_review"
        return "succeeded"
    job.last_error = f"{failures} page(s) failed"
    if job.attempts < job.max_attempts:
        job.status = "queued"; job.locked_until = None
        job.next_attempt_at = now() + timedelta(seconds=cfg.backoff_base_seconds * 2 ** (job.attempts - 1))
        doc.status = "processing"
        audit(s, SYSTEM, "job.retry_scheduled", "job", job.id, {"attempt": job.attempts})
        return "retry"
    job.status, job.locked_until, doc.status = "partial_failure", None, "partial_failure"
    audit(s, SYSTEM, "job.dead", "job", job.id, {"failures": failures})
    return "partial_failure"


def run_once(sf, cfg: Settings, engine) -> str | None:
    with sf() as s:
        job = claim_next(s, cfg)
        if not job:
            return None
        s.commit()                                         # persist lease before long work
        out = process_job(s, cfg, engine, job)
        s.commit()
        return out

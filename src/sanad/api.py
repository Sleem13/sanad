"""FastAPI app (modular monolith). Every content endpoint enforces role + organizational scope server-side."""
from __future__ import annotations
import logging, json, sys
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Header, Query, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy import text
from .auth import Principal, Forbidden, principal_from_token
from .config import Settings
from . import db as D, ingest as I, review as R, export as X

log = logging.getLogger("sanad")


class JsonFmt(logging.Formatter):
    def format(self, r):
        return json.dumps({"ts": self.formatTime(r), "level": r.levelname, "msg": r.getMessage(), "logger": r.name}, ensure_ascii=False)

class RecognizeIn(BaseModel):
    engine: str | None = None


class Edit(BaseModel):
    region_id: str
    text: str | None = None
    status: str | None = None

class DraftIn(BaseModel):
    base_version_no: int
    edits: list[Edit]
    reason: str | None = None

class ApproveIn(BaseModel):
    version_no: int

class ReopenIn(BaseModel):
    reason: str

class AssignIn(BaseModel):
    assignee: str

class NoteIn(BaseModel):
    note: str


def create_app(cfg: Settings | None = None) -> FastAPI:
    cfg = cfg or Settings.from_env()
    cfg.ensure_dirs()
    h = logging.StreamHandler(sys.stdout); h.setFormatter(JsonFmt())
    logging.basicConfig(level=logging.INFO, handlers=[h], force=False)
    sf = D.make_session_factory(cfg.db_url)
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def lifespan(instance):
        yield
        instance.state.vlm.stop()
    app = FastAPI(title="SANAD pilot API", version="0.1.0", lifespan=lifespan)
    app.state.cfg, app.state.sf = cfg, sf
    # Understanding tasks are owned by this single API process, not an external
    # worker. A previous process cannot finish a persisted running task.
    with sf() as recovery:
        for row in recovery.query(D.UnderstandingRun).filter_by(status="running"):
            row.status, row.error = "failed", "interrupted_by_server_restart"
        recovery.commit()
    import threading
    app.state.step_lock = threading.Lock()
    from .vlm_runtime import VLMRuntime
    app.state.vlm = VLMRuntime(cfg.data_dir)
    import secrets
    app.state.local_session = secrets.token_urlsafe(32)

    def session():
        with sf() as s:
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise

    def me(request: Request, authorization: str | None = Header(default=None)) -> Principal:
        if (not authorization and cfg.env == "dev" and cfg.dev_super_admin
                and secrets.compare_digest(request.cookies.get("sanad_local_session", ""), app.state.local_session)):
            return Principal("local.super_admin", frozenset({"super_admin"}), frozenset({"*"}))
        tok = authorization.removeprefix("Bearer ").strip() if authorization else None
        p = principal_from_token(cfg.users, tok)
        if not p:
            raise HTTPException(401, "invalid or missing token")
        return p

    @app.exception_handler(Forbidden)
    async def _forbidden(_, e):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": str(e)}, status_code=403)

    @app.exception_handler(R.Conflict)
    async def _conflict(_, e):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": str(e)}, status_code=409)

    @app.exception_handler(R.Invalid)
    async def _invalid(_, e):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": str(e)}, status_code=422)

    def doc_or_404(s, who: Principal, doc_id: str, perm="read_content") -> D.Document:
        doc = s.get(D.Document, doc_id)
        # Same 404 for "missing" and "not yours" so existence is not leaked across org scopes.
        if not doc or not who.can_see_org(doc.org_scope):
            raise HTTPException(404, "not found")
        if not who.has(perm):
            raise HTTPException(403, f"missing permission {perm}")
        return doc

    def page_or_404(s, who: Principal, page_id: str, perm="read_content") -> D.Page:
        pg = s.get(D.Page, page_id)
        if not pg:
            raise HTTPException(404, "not found")
        doc_or_404(s, who, pg.document_id, perm)
        return pg

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "env": cfg.env, "engine": cfg.engine, "external_processing": cfg.allow_external_processing,
                "local_super_admin": cfg.env == "dev" and cfg.dev_super_admin}

    @app.post("/api/v1/dev/session")
    def local_admin_session(request: Request, response: Response):
        if cfg.env != "dev" or not cfg.dev_super_admin:
            raise HTTPException(404, "not found")
        if not request.client or request.client.host not in {"127.0.0.1", "::1"}:
            raise HTTPException(403, "local development session requires a loopback connection")
        origin = request.headers.get("origin")
        if origin and origin != f"{request.url.scheme}://{request.url.netloc}":
            raise HTTPException(403, "cross-origin session request refused")
        response.set_cookie("sanad_local_session", app.state.local_session, httponly=True, samesite="strict", path="/")
        return {"user": "local.super_admin", "role": "super_admin"}

    @app.get("/readyz")
    def readyz(s=Depends(session)):
        s.execute(text("select 1"))
        ok = cfg.data_dir.exists()
        if not ok:
            raise HTTPException(503, "storage unavailable")
        return {"status": "ready"}

    @app.post("/api/v1/documents", status_code=201)
    async def upload(file: UploadFile = File(...), org_scope: str = Form(...), demo: bool = Form(False),
                     who: Principal = Depends(me), s=Depends(session)):
        who.require("ingest", org_scope)
        data = await file.read(cfg.max_upload_bytes + 1)
        art, doc, dup = I.ingest_bytes(s, cfg, data=data, filename=file.filename or "upload", org_scope=org_scope,
                                       actor=who.user, demo=demo)
        if art.status == "quarantined":
            return {"artifact_id": art.id, "status": "quarantined", "reason": art.quarantine_reason}
        return {"artifact_id": art.id, "document_id": doc.id if doc else None, "status": "accepted", "duplicate_file": dup}

    @app.get("/api/v1/documents/{doc_id}")
    def get_doc(doc_id: str, who: Principal = Depends(me), s=Depends(session)):
        doc = doc_or_404(s, who, doc_id)
        pages = s.query(D.Page).filter_by(document_id=doc.id).order_by(D.Page.page_no).all()
        jobs = s.query(D.Job).filter_by(document_id=doc.id).all()
        sequence = {event.object_id: event.seq for event in s.query(D.AuditEvent).filter(
            D.AuditEvent.object_type == "job", D.AuditEvent.action == "job.enqueued",
            D.AuditEvent.object_id.in_([job.id for job in jobs])).order_by(D.AuditEvent.seq)}
        art = s.get(D.SourceArtifact, doc.artifact_id)
        return {"id": doc.id, "filename": art.original_filename, "status": doc.status, "org_scope": doc.org_scope,
                "pages": [{"id": p.id, "page_no": p.page_no, "status": p.status} for p in pages],
                "jobs": [{"id": j.id, "sequence": sequence.get(j.id, 0), "status": j.status, "engine": j.engine_id, "attempts": j.attempts,
                          "cancel_requested": j.cancel_requested, "last_error": j.last_error} for j in jobs],
                "deliveries": [{"id": d.id, "status": d.status, "errors": d.errors} for d in
                               s.query(D.DeliveryRecord).filter_by(document_id=doc.id).all()]}

    @app.get("/api/v1/me")
    def identity(who: Principal = Depends(me)):
        from .auth import PERMISSIONS
        return {"user": who.user, "roles": sorted(who.roles), "orgs": sorted(who.orgs),
                "permissions": sorted(set().union(*(PERMISSIONS.get(r, set()) for r in who.roles)))}

    @app.get("/api/v1/documents")
    def list_docs(q: str = "", status: str = "", limit: int = Query(100, ge=1, le=200),
                  who: Principal = Depends(me), s=Depends(session)):
        who.require("read_content")
        query = s.query(D.Document, D.SourceArtifact).join(D.SourceArtifact)
        if "*" not in who.orgs:
            query = query.filter(D.Document.org_scope.in_(who.orgs))
        if status:
            query = query.filter(D.Document.status == status)
        if q:
            query = query.filter(D.SourceArtifact.original_filename.contains(q, autoescape=True))
        return {"items": [{"id": d.id, "filename": a.original_filename, "org_scope": d.org_scope,
                           "status": d.status, "pages": d.page_count, "demo": a.is_synthetic_demo,
                           "created_at": d.created_at.isoformat()} for d, a in
                          query.order_by(D.Document.created_at.desc()).limit(limit).all()]}

    @app.get("/api/v1/system")
    def system_info(who: Principal = Depends(me), s=Depends(session)):
        if not (who.has("read_content") or who.has("admin_ops")):
            raise Forbidden("missing system access")
        s.execute(text("select 1"))
        return {"environment": cfg.env, "engine": cfg.engine, "external_processing": cfg.allow_external_processing,
                "database": "ready", "storage": "ready" if cfg.data_dir.exists() else "unavailable",
                "max_upload_mb": cfg.max_upload_bytes / 1024 ** 2,
                "supported_uploads": list(I.ALLOWED),
                "worker": "On-demand local model worker",
                "models": [{"id": "paddleocr_vl", "state": app.state.vlm.status()["state"]},
                           {"id": "paddleocr_arabic", "state": "local Arabic PP-OCRv5 CPU runtime"},
                           {"id": "gemma", "state": "Local Ollama field extraction"}],
                "training": "No trained SANAD checkpoint or verified training GPU"}

    def job_or_404(s, who, job_id):
        job = s.get(D.Job, job_id)
        if not job:
            raise HTTPException(404, "not found")
        doc = doc_or_404(s, who, job.document_id)
        if not (who.has("ingest") or who.has("assign")):
            raise Forbidden("job control requires operator or supervisor")
        return job, doc

    @app.post("/api/v1/jobs/{job_id}/cancel")
    def cancel_job(job_id: str, who: Principal = Depends(me), s=Depends(session)):
        job, doc = job_or_404(s, who, job_id)
        if job.status not in {"queued", "running", "blocked"}:
            raise R.Conflict("only queued, running or blocked jobs can be cancelled")
        job.cancel_requested = True
        if job.status != "running":
            job.status, job.locked_until = "cancelled", None
        D.audit(s, who.user, "job.cancel_requested", "job", job.id)
        return {"status": job.status, "cancel_requested": True}

    @app.post("/api/v1/jobs/{job_id}/retry")
    def retry_job(job_id: str, who: Principal = Depends(me), s=Depends(session)):
        job, doc = job_or_404(s, who, job_id)
        if job.status not in {"blocked", "failed", "partial_failure", "cancelled"}:
            raise R.Conflict("job is not retryable")
        if doc.status == "approved":
            raise R.Conflict("approved documents cannot be retried")
        job.status, job.cancel_requested, job.locked_until = "queued", False, None
        job.attempts, job.next_attempt_at, job.last_error = 0, D.now(), None
        doc.status = "ingested"
        D.audit(s, who.user, "job.retry_requested", "job", job.id)
        return {"status": job.status}

    @app.post("/api/v1/documents/{doc_id}/recognize", status_code=202)
    def recognize_document(doc_id: str, body: RecognizeIn | None = None, who: Principal = Depends(me), s=Depends(session)):
        doc = doc_or_404(s, who, doc_id)
        if not (who.has("ingest") or who.has("assign")):
            raise Forbidden("job control requires operator or supervisor")
        engine_id = (body.engine if body else None) or cfg.engine
        if engine_id not in {"paddleocr_arabic", "paddleocr_vl", "paddleocr_vl_full_page"}:
            raise R.Invalid("select a supported real pipeline")
        if engine_id in {"paddleocr_vl", "paddleocr_vl_full_page"} and app.state.vlm.status()["state"] != "ready":
            raise R.Invalid("Start the local VLM in Model controls and wait until ready")
        if any(p.status == "approved" for p in s.query(D.Page).filter_by(document_id=doc.id)):
            raise R.Conflict("approved page must be reopened before reprocessing")
        if s.query(D.Job).filter_by(document_id=doc.id, status="running").first():
            raise R.Conflict("OCR job is already running")
        if not app.state.step_lock.acquire(blocking=False):
            raise R.Conflict("OCR worker is busy; try again when current processing completes")
        try:
            from datetime import timedelta
            job = s.query(D.Job).filter_by(document_id=doc.id, engine_id=engine_id, status="queued").first()
            job = job or I.enqueue(s, cfg, doc, who.user, engine_id=engine_id, tag=D.uid())
            job.status, job.attempts = "running", job.attempts + 1
            job.locked_until = D.now() + timedelta(seconds=2400)
            doc.status = "processing"
            job_id = job.id
            D.audit(s, who.user, "job.real_ocr_started", "job", job.id)
            s.commit()

            def work_selected():
                try:
                    from .engines.paddleocr_arabic import PaddleArabicEngine
                    from .pipeline import process_job
                    with sf() as worker_session:
                        selected = worker_session.get(D.Job, job_id)
                        from .engines.local_vlm import LocalVLMEngine
                        from .engines.full_page_vlm import FullPageVLMEngine
                        if selected.engine_id == "paddleocr_vl_full_page":
                            engine = FullPageVLMEngine(cfg.data_dir, api_key=app.state.vlm.key)
                        elif selected.engine_id == "paddleocr_vl":
                            engine = LocalVLMEngine(cfg.data_dir, api_key=app.state.vlm.key)
                        else:
                            engine = PaddleArabicEngine()
                        process_job(worker_session, cfg, engine, selected)
                        worker_session.commit()
                except Exception as exc:
                    log.exception("Arabic OCR job failed: %s", job_id)
                    with sf() as failed_session:
                        selected = failed_session.get(D.Job, job_id)
                        selected.status, selected.last_error = "failed", f"Paddle OCR worker failed: {type(exc).__name__}"
                        selected.locked_until = None
                        for run in failed_session.query(D.ProcessingRun).filter_by(job_id=job_id, status="running"):
                            run.status, run.error, run.finished_at = "failed", type(exc).__name__, D.now()
                        failed_session.get(D.Document, selected.document_id).status = "failed"
                        D.audit(failed_session, "system.worker", "job.failed", "job", job_id,
                                {"error_type": type(exc).__name__})
                        failed_session.commit()
                finally:
                    app.state.step_lock.release()

            app.state.worker_thread = threading.Thread(target=work_selected, name="sanad-arabic-ocr", daemon=True)
            app.state.worker_thread.start()
            return {"job_id": job_id, "status": "running", "engine": engine_id, "is_mock": False}
        except Exception:
            app.state.step_lock.release()
            raise

    @app.post("/api/v1/pages/{page_id}/assign")
    def assign_page(page_id: str, body: AssignIn, who: Principal = Depends(me), s=Depends(session)):
        pg = page_or_404(s, who, page_id, "assign")
        org = s.get(D.Document, pg.document_id).org_scope
        candidates = [u for u in cfg.users.values() if u["user"] == body.assignee
                      and (org in u["orgs"] or "*" in u["orgs"]) and "reviewer" in u["roles"]]
        if not candidates:
            raise R.Invalid("assignee must be a reviewer in the document organization")
        R.assign(s, who, page_id, body.assignee)
        return {"status": "assigned"}

    @app.post("/api/v1/pages/{page_id}/escalate")
    def escalate_page(page_id: str, body: NoteIn, who: Principal = Depends(me), s=Depends(session)):
        page_or_404(s, who, page_id, "edit")
        if not body.note.strip():
            raise R.Invalid("escalation note required")
        if not s.query(D.ReviewTask).filter_by(page_id=page_id).first():
            raise R.Invalid("page has no review task")
        R.escalate(s, who, page_id, body.note)
        return {"status": "escalated"}

    @app.get("/api/v1/pages/{page_id}/image")
    def page_image(page_id: str, who: Principal = Depends(me), s=Depends(session)):
        pg = page_or_404(s, who, page_id)
        art = s.get(D.SourceArtifact, s.get(D.Document, pg.document_id).artifact_id)
        D.audit(s, who.user, "content.image_read", "page", page_id)
        return FileResponse(art.storage_path, media_type=art.media_type)

    @app.get("/api/v1/pages/{page_id}/content")
    def page_content(page_id: str, who: Principal = Depends(me), s=Depends(session)):
        pg = page_or_404(s, who, page_id)
        vs = s.query(D.PageVersion).filter_by(page_id=page_id).order_by(D.PageVersion.version_no).all()
        if not vs:
            raise HTTPException(409, "not processed yet")
        cur = vs[-1]
        cs = s.query(D.Correction).filter_by(page_id=page_id).order_by(D.Correction.created_at).all()
        return {"page_id": page_id, "page_status": pg.status, "version_no": cur.version_no, "kind": cur.kind,
                "is_mock": cur.is_mock, "content": cur.content,
                "history": [{"version_no": v.version_no, "kind": v.kind, "author": v.author} for v in vs],
                "corrections": [{"region_id": c.region_id, "old": c.old_text, "new": c.new_text, "reason": c.reason,
                                 "author": c.author} for c in cs]}



    @app.put("/api/v1/pages/{page_id}/draft")
    def draft(page_id: str, body: DraftIn, who: Principal = Depends(me), s=Depends(session)):
        page_or_404(s, who, page_id, "edit")
        v = R.save_draft(s, who, page_id, body.base_version_no, [e.model_dump(exclude_unset=True) for e in body.edits], body.reason)
        return {"version_no": v.version_no, "kind": v.kind}


    @app.post("/api/v1/pages/{page_id}/approve")
    def approve(page_id: str, body: ApproveIn, who: Principal = Depends(me), s=Depends(session)):
        page_or_404(s, who, page_id, "approve")
        v = R.approve(s, who, page_id, body.version_no)
        return {"version_no": v.version_no, "kind": v.kind}


    @app.post("/api/v1/pages/{page_id}/reopen")
    def reopen(page_id: str, body: ReopenIn, who: Principal = Depends(me), s=Depends(session)):
        page_or_404(s, who, page_id, "reopen")
        v = R.reopen(s, who, page_id, body.reason)
        return {"version_no": v.version_no, "kind": v.kind}

    @app.post("/api/v1/documents/{doc_id}/export")
    def export(doc_id: str, who: Principal = Depends(me), s=Depends(session)):
        doc_or_404(s, who, doc_id, "export")
        rec = X.export_document(s, who, doc_id)
        return {"delivery_id": rec.id, "status": rec.status, "errors": rec.errors, "payload": rec.payload}

    @app.get("/api/v1/audit/verify")
    def audit_verify(who: Principal = Depends(me), s=Depends(session)):
        who.require("read_audit")
        ok, bad = D.verify_audit_chain(s)
        return {"intact": ok, "first_bad_seq": bad}

    from .vlm_api import install_vlm_routes
    install_vlm_routes(app, cfg, me, session, page_or_404)
    from .dataset_ui import install_dataset_routes
    install_dataset_routes(app, cfg, me)
    static_dir = Path(__file__).resolve().parents[2] / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", response_class=HTMLResponse)
    @app.get("/review", response_class=HTMLResponse)
    def review_ui():
        return (static_dir / "index.html").read_text(encoding="utf-8")

    return app

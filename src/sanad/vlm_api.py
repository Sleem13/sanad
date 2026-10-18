"""Authenticated model controls and version-bound Gemma extraction."""
import json
import os
import threading
from urllib.request import urlopen
from fastapi import Depends, HTTPException
from . import db as D, review as R
from .engines.base import EngineUnavailable


def install_vlm_routes(app, cfg, me, session, page_or_404):
    def info():
        result = app.state.vlm.status()
        try:
            with urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as response:
                models = json.load(response)["models"]
            result["gemma_ready"] = any(m["name"] == result["gemma_model"] for m in models)
        except Exception:
            result["gemma_ready"] = False
        return result

    @app.get("/api/v1/models/runtime")
    def status(who=Depends(me)):
        if not (who.has("read_content") or who.has("admin_ops")):
            raise HTTPException(403, "model access required")
        return info()

    @app.post("/api/v1/models/{command}")
    def control(command: str, who=Depends(me), s=Depends(session)):
        who.require("admin_ops")
        if command not in {"start", "stop"}:
            raise HTTPException(404, "not found")
        if not app.state.step_lock.acquire(blocking=False):
            raise R.Conflict("model worker is busy")
        try:
            try:
                result = getattr(app.state.vlm, command)()
            except EngineUnavailable as exc:
                raise R.Invalid(str(exc))
            D.audit(s, who.user, "model." + command, "model", "paddleocr_vl")
            return result
        finally:
            app.state.step_lock.release()

    def serialize(run):
        return {"id": run.id, "version_id": run.version_id, "status": run.status,
                "model": run.model, "result": run.result, "error": run.error}

    @app.get("/api/v1/pages/{page_id}/understanding")
    def get_understanding(page_id: str, who=Depends(me), s=Depends(session)):
        page_or_404(s, who, page_id)
        version = R.latest(s, page_id)
        run = s.query(D.UnderstandingRun).filter_by(page_id=page_id, version_id=version.id).order_by(D.UnderstandingRun.created_at.desc()).first() if version else None
        return serialize(run) if run else {"status": "not_processed"}

    @app.post("/api/v1/pages/{page_id}/understanding", status_code=202)
    def start_understanding(page_id: str, who=Depends(me), s=Depends(session)):
        page_or_404(s, who, page_id, "edit")
        version = R.latest(s, page_id)
        if not version or version.is_mock:
            raise R.Invalid("a real transcription is required")
        if not info()["gemma_ready"]:
            raise R.Invalid("Gemma is not installed; run ollama pull gemma3:4b")
        if not app.state.step_lock.acquire(blocking=False):
            raise R.Conflict("model worker is busy")
        try:
            content = version.content
            run = D.UnderstandingRun(page_id=page_id, version_id=version.id,
                model=os.getenv("SANAD_GEMMA_MODEL", "gemma3:4b"), status="running")
            s.add(run); s.flush(); run_id = run.id
            D.audit(s, who.user, "understanding.started", "page", page_id, {"version_id": version.id})
            s.commit()
            def work():
                try:
                    from .understanding import extract
                    result = extract(content)
                    with app.state.sf() as worker:
                        row = worker.get(D.UnderstandingRun, run_id)
                        row.result, row.status = result, "succeeded"
                        D.audit(worker, "system.worker", "understanding.completed", "page", page_id)
                        worker.commit()
                except Exception as exc:
                    with app.state.sf() as worker:
                        row = worker.get(D.UnderstandingRun, run_id)
                        row.status, row.error = "failed", type(exc).__name__
                        worker.commit()
                finally:
                    app.state.step_lock.release()
            app.state.understanding_thread = threading.Thread(target=work, daemon=True, name="sanad-gemma")
            app.state.understanding_thread.start()
            return {"id": run_id, "status": "running"}
        except Exception:
            app.state.step_lock.release()
            raise

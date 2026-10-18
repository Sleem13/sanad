"""Development-only public-corpus review, isolated from legal-document approval."""
import json
import threading
from pathlib import Path

from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .auth import Principal
from .db import now


class DatasetEdit(BaseModel):
    text: str
    note: str
    base_revision: int
    checked_against_image: bool


def install_dataset_routes(app, cfg, me):
    root = cfg.data_dir / "research" / "egyptian-eval"
    lock = threading.Lock()

    def access(who: Principal, write=False):
        if cfg.env != "dev":
            raise HTTPException(404, "public dataset workbench is dev-only")
        who.require("edit" if write else "read_content")

    def records():
        source = root / "pending_review.jsonl"
        if not source.exists():
            return []
        return [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]

    def reviewed():
        path = root / "reviewed.jsonl"
        return {r["id"]: r for r in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())} if path.exists() else {}

    def find(item_id):
        row = next((r for r in records() if r["id"] == item_id), None)
        if not row:
            raise HTTPException(404, "example not found")
        return row

    @app.get("/api/v1/dataset")
    def dataset_list(who: Principal = Depends(me)):
        access(who)
        done = reviewed()
        return {"name": "Egyptian official documents · public sample", "items": [
            {"id": r["id"], "document_id": r["document_id"], "page": r["source_page"],
             "reviewed": r["id"] in done, "notes": len(r.get("review_notes") or [])} for r in records()]}

    @app.get("/api/v1/dataset/{item_id}")
    def dataset_item(item_id: str, who: Principal = Depends(me)):
        access(who)
        row = find(item_id)
        return {**row, **reviewed().get(item_id, {}), "review_revision": reviewed().get(item_id, {}).get("review_revision", 0)}

    @app.get("/api/v1/dataset/{item_id}/image")
    def dataset_image(item_id: str, who: Principal = Depends(me)):
        access(who)
        path = (root / find(item_id)["image"]).resolve()
        if not path.is_relative_to((root / "images").resolve()):
            raise HTTPException(422, "invalid image path")
        return FileResponse(path, media_type="image/png")

    @app.put("/api/v1/dataset/{item_id}/review")
    def dataset_review(item_id: str, body: DatasetEdit, who: Principal = Depends(me)):
        access(who, True)
        if not body.checked_against_image or not body.note.strip():
            raise HTTPException(422, "confirm visual review and provide a review note")
        with lock:
            row, done = find(item_id), reviewed()
            current = done.get(item_id, {}).get("review_revision", 0)
            if current != body.base_revision:
                raise HTTPException(409, "review changed; reload before saving")
            old = done.get(item_id, row)
            revision = current + 1
            entry = {**row, "text": body.text, "reviewed": True, "review_revision": revision,
                     "reviewed_by": who.user, "reviewed_at": now().isoformat(), "review_note": body.note,
                     "review_history": old.get("review_history", []) + [
                         {"revision": revision, "author": who.user, "at": now().isoformat(),
                          "previous_text": old["text"], "note": body.note}]}
            done[item_id] = entry
            temp = root / "reviewed.jsonl.tmp"
            temp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in done.values()), encoding="utf-8")
            temp.replace(root / "reviewed.jsonl")
        return {"status": "reviewed", "review_revision": revision}

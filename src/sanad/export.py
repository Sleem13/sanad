"""Owner-Schema adapter. The real Schema is NOT known: schemas/owner_schema.provisional.json is a placeholder contract.
Export uses APPROVED versions only, validates strictly (jsonschema), and either delivers fully or rejects with errors."""
from __future__ import annotations
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from sqlalchemy.orm import Session
from .auth import Principal
from .canonical import CanonicalPage
from .db import Document, Page, PageVersion, SourceArtifact, DeliveryRecord, audit

DEFAULT_SCHEMA = Path(__file__).resolve().parents[2] / "schemas" / "owner_schema.provisional.json"


def build_payload(s: Session, doc: Document) -> tuple[dict, list[str], list[str]]:
    art = s.get(SourceArtifact, doc.artifact_id)
    pages_out, errors, vids, demo = [], [], [], False
    for p in s.query(Page).filter_by(document_id=doc.id).order_by(Page.page_no):
        v = s.query(PageVersion).filter_by(page_id=p.id).order_by(PageVersion.version_no.desc()).first()
        if not v or v.kind != "approved":
            errors.append(f"page {p.page_no}: no approved version")
            continue
        if v.is_mock:
            errors.append(f"page {p.page_no}: mock-engine content is not exportable")
            continue
        cp = CanonicalPage.model_validate(v.content)
        vids.append(v.id)
        demo = demo or v.is_mock
        pages_out.append({"page_no": p.page_no, "approved_version_id": v.id, "text": cp.text_in_reading_order(),
                          "regions": [{"region_id": r.region_id, "label": r.label, "bbox": r.bbox, "text": r.text,
                                       "status": r.status.value,
                                       **({"cells": [c.model_dump(mode="json") for c in r.cells]} if r.cells else {})} for r in cp.regions]})
    payload = {"demo_only": demo, "document_id": doc.id, "source_sha256": art.sha256, "page_count": len(pages_out), "pages": pages_out}
    return payload, errors, vids


def export_document(s: Session, who: Principal, doc_id: str, schema_path: Path | None = None) -> DeliveryRecord:
    doc = s.get(Document, doc_id)
    who.require("export", doc.org_scope)
    schema = json.loads(Path(schema_path or DEFAULT_SCHEMA).read_text())
    payload, errors, vids = build_payload(s, doc)
    if not errors:
        errors = [f"{'/'.join(map(str, e.path))}: {e.message}" for e in Draft202012Validator(schema).iter_errors(payload)]
    rec = DeliveryRecord(document_id=doc_id, schema_name=schema.get("title", "owner-schema"),
                         schema_version=schema.get("$comment", "provisional"),
                         status="rejected" if errors else "delivered", errors=errors,
                         payload=None if errors else payload, source_version_ids=vids, created_by=who.user)
    s.add(rec); s.flush()
    audit(s, who.user, "export.rejected" if errors else "export.delivered", "document", doc_id, {"errors": errors[:5]})
    return rec

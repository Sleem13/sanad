"""Versioned corrections with optimistic concurrency. Saving a draft NEVER approves. Approved versions are immutable;
reopening creates a new draft whose parent is the approved version (the approved row is untouched)."""
from __future__ import annotations
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .auth import Principal, Forbidden
from .canonical import CanonicalPage, RegionStatus
from .db import Page, PageVersion, ReviewTask, Correction, Approval, Document, audit, now


class Conflict(Exception):
    pass


class Invalid(Exception):
    pass


def latest(s: Session, page_id: str) -> PageVersion:
    v = s.query(PageVersion).filter_by(page_id=page_id).order_by(PageVersion.version_no.desc()).first()
    if not v:
        raise Invalid("page has no content yet")
    return v


def _org(s: Session, page: Page) -> str:
    return s.get(Document, page.document_id).org_scope


def save_draft(s: Session, who: Principal, page_id: str, base_version_no: int, edits: list[dict], reason: str | None) -> PageVersion:
    page = s.get(Page, page_id)
    who.require("edit", _org(s, page))
    cur = latest(s, page_id)
    if cur.kind == "approved":
        raise Conflict("page is approved; reopen it (supervisor) before editing")
    if cur.version_no != base_version_no:
        raise Conflict(f"stale base version {base_version_no}; current is {cur.version_no}")
    content = CanonicalPage.model_validate(cur.content)
    by_id = {r.region_id: r for r in content.regions}
    new_corrections = []
    for e in edits:
        r = by_id.get(e["region_id"])
        if r is None:
            raise Invalid(f"unknown region {e['region_id']}")
        old = r.text
        if "text" in e:
            r.text = e["text"] if (e["text"] or "").strip() else None
            if r.label == "table":
                from .table_structure import table_cells
                from .canonical import TableCell
                r.cells = [TableCell(**cell) for cell in table_cells(r.text) or []] or None
        if "status" in e:
            r.status = RegionStatus(e["status"])
        if r.label == "table" and r.cells:
            for cell in r.cells:
                cell.status = r.status
        if r.status == RegionStatus.recognized and not r.text and r.label not in {"seal", "image", "signature", "stamp", "figure", "chart"}:
            raise Invalid(f"region {r.region_id}: recognized requires text; use illegible/not_present instead")
        if r.status in (RegionStatus.not_present, RegionStatus.not_processed):
            r.text = None
        r.flags = sorted(set(r.flags) | {"human_edited"})
        new_corrections.append((r.region_id, old, r.text))
    content = CanonicalPage.model_validate(content.model_dump())     # re-validate after edits
    v = PageVersion(page_id=page_id, version_no=cur.version_no + 1, kind="draft", parent_version_id=cur.id,
                    content=content.model_dump(mode="json"), author=who.user, is_mock=cur.is_mock)
    try:
        with s.begin_nested():
            s.add(v); s.flush()
    except IntegrityError:
        raise Conflict("concurrent edit detected")
    for rid, old, new in new_corrections:
        s.add(Correction(page_id=page_id, version_id=v.id, region_id=rid, old_text=old, new_text=new,
                         reason=reason, author=who.user))
    task = s.query(ReviewTask).filter_by(page_id=page_id).first()
    if task:
        task.status, task.assignee, task.updated_at = "in_progress", task.assignee or who.user, now()
    audit(s, who.user, "review.draft_saved", "page", page_id, {"version_no": v.version_no, "edits": len(edits)})
    return v


def approve(s: Session, who: Principal, page_id: str, version_no: int) -> PageVersion:
    page = s.get(Page, page_id)
    who.require("approve", _org(s, page))
    cur = latest(s, page_id)
    if cur.version_no != version_no:
        raise Conflict(f"stale version {version_no}; current is {cur.version_no}")
    if cur.kind == "approved":
        return cur                                                    # idempotent
    if cur.is_mock:
        raise Invalid("legacy synthetic content cannot be approved; run a real OCR pipeline")
    CanonicalPage.model_validate(cur.content)
    unresolved = [r["region_id"] for r in cur.content["regions"] if r["status"] in ("requires_review", "uncertain")]
    if unresolved:
        raise Invalid(f"unresolved regions: {unresolved}")
    v = PageVersion(page_id=page_id, version_no=cur.version_no + 1, kind="approved", parent_version_id=cur.id,
                    content=cur.content, author=who.user, is_mock=cur.is_mock)
    try:
        with s.begin_nested():
            s.add(v); s.flush()
    except IntegrityError:
        raise Conflict("concurrent change detected")
    s.add(Approval(page_id=page_id, version_id=v.id, approved_by=who.user))
    page.status = "approved"
    t = s.query(ReviewTask).filter_by(page_id=page_id).first()
    if t:
        t.status, t.updated_at = "approved", now()
    doc = s.get(Document, page.document_id)
    if all(p.status == "approved" for p in s.query(Page).filter_by(document_id=doc.id)):
        doc.status = "approved"
    audit(s, who.user, "review.approved", "page", page_id, {"version_no": v.version_no})
    return v


def reopen(s: Session, who: Principal, page_id: str, reason: str) -> PageVersion:
    page = s.get(Page, page_id)
    who.require("reopen", _org(s, page))
    if not reason:
        raise Invalid("reason required to reopen")
    cur = latest(s, page_id)
    if cur.kind != "approved":
        raise Invalid("page is not approved")
    v = PageVersion(page_id=page_id, version_no=cur.version_no + 1, kind="draft", parent_version_id=cur.id,
                    content=cur.content, author=who.user, is_mock=cur.is_mock)
    s.add(v); s.flush()
    page.status = "in_review"
    s.get(Document, page.document_id).status = "in_review"
    t = s.query(ReviewTask).filter_by(page_id=page_id).first()
    if t:
        t.status = "reopened"
    audit(s, who.user, "review.reopened", "page", page_id, {"reason": reason, "from_version": cur.version_no})
    return v


def assign(s: Session, who: Principal, page_id: str, assignee: str) -> None:
    page = s.get(Page, page_id)
    who.require("assign", _org(s, page))
    t = s.query(ReviewTask).filter_by(page_id=page_id).first()
    if not t:
        raise Invalid("no review task")
    audit(s, who.user, "review.assigned", "page", page_id, {"from": t.assignee, "to": assignee})
    t.assignee, t.updated_at = assignee, now()


def escalate(s: Session, who: Principal, page_id: str, note: str) -> None:
    page = s.get(Page, page_id)
    who.require("edit", _org(s, page))
    t = s.query(ReviewTask).filter_by(page_id=page_id).first()
    t.status, t.escalation_note, t.updated_at = "escalated", note, now()
    audit(s, who.user, "review.escalated", "page", page_id, {"note": note})

import io, os, stat, pytest
from conftest import png_bytes, upload, work, H, first_page
from fakes import StubEngine
from sanad.engines.base import EngineUnavailable
from sanad import db as D
from sanad.canonical import CanonicalPage, Region
from pydantic import ValidationError


# ---------- ingestion ----------
def test_repeated_ingestion_is_idempotent_and_does_not_duplicate_documents(env):
    data = png_bytes()
    a = upload(env, data).json(); b = upload(env, data).json()
    assert a["artifact_id"] == b["artifact_id"] and b["duplicate_file"] is True and a["document_id"] == b["document_id"]
    with env.sf() as s:
        assert s.query(D.Document).count() == 1 and s.query(D.Job).count() == 1


def test_same_bytes_in_other_org_is_a_separate_record(env):
    data = png_bytes()
    a = upload(env, data).json()
    c = env.client.post("/api/v1/documents", headers=H("demo-operator-b"), data={"org_scope": "demo-court-b"},
                        files={"file": ("x.png", data)}).json()
    assert a["artifact_id"] != c["artifact_id"]          # similar content never merges independent records


@pytest.mark.parametrize("payload,reason", [
    (b"", "empty_file"),
    (b"not an image at all", "corrupt_or_unreadable"),
    (png_bytes()[:60], "corrupt_or_unreadable"),                     # truncated PNG
])
def test_invalid_or_corrupt_files_are_quarantined(env, payload, reason):
    r = upload(env, payload).json()
    assert r["status"] == "quarantined" and r["reason"].startswith(reason)
    with env.sf() as s:
        assert s.query(D.Document).count() == 0


def test_oversized_pixel_count_rejected(env):
    env.cfg.max_image_pixels = 1000
    r = upload(env, png_bytes(size=(100, 100))).json()
    assert r["status"] == "quarantined"


def test_hostile_filename_never_used_as_path(env):
    r = upload(env, png_bytes(), name="../../etc/passwd").json()
    assert r["status"] == "accepted"
    with env.sf() as s:
        art = s.get(D.SourceArtifact, r["artifact_id"])
        assert str(env.cfg.data_dir) in art.storage_path and "passwd" not in art.storage_path


def test_original_is_preserved_readonly_and_byte_identical(env):
    data = png_bytes()
    r = upload(env, data).json()
    work(env)
    with env.sf() as s:
        p = s.get(D.SourceArtifact, r["artifact_id"]).storage_path
    assert open(p, "rb").read() == data
    assert not (os.stat(p).st_mode & stat.S_IWUSR)


# ---------- worker ----------
def test_worker_failure_then_retry_succeeds(env):
    doc = upload(env, png_bytes()).json()["document_id"]
    eng = StubEngine(fail_pages={1}, fail_times=1)
    assert work(env, eng)[0] == "retry"
    assert work(env, eng)[0] == "succeeded"
    with env.sf() as s:
        job = s.query(D.Job).one()
        assert job.status == "succeeded" and job.attempts == 2
        assert s.query(D.PageVersion).filter_by(kind="raw").count() == 1       # exactly one effect


def test_retries_are_bounded_then_partial_failure(env):
    upload(env, png_bytes())
    eng = StubEngine(fail_pages={1}, fail_times=99)
    outs = work(env, eng, 4)
    assert outs[:2] == ["retry", "retry"] and outs[2] == "partial_failure" and outs[3] is None
    with env.sf() as s:
        assert s.query(D.Job).one().attempts == 3
        assert s.query(D.Document).one().status == "partial_failure"


def test_crashed_worker_lease_expiry_is_reclaimed(env):
    upload(env, png_bytes())
    from datetime import timedelta
    with env.sf() as s:
        j = s.query(D.Job).one(); j.status = "running"; j.attempts = 1
        j.locked_until = D.now() - timedelta(seconds=1); s.commit()
    assert work(env)[0] == "succeeded"


def test_partial_document_failure_isolated_per_page(env):
    doc_id = upload(env, png_bytes()).json()["document_id"]
    with env.sf() as s:                                   # add a 2nd page to the same logical document
        s.add(D.Page(document_id=doc_id, page_no=2, width=400, height=600)); s.commit()
    assert work(env, StubEngine(fail_pages={2}, fail_times=1))[0] == "retry"
    with env.sf() as s:
        st = {p.page_no: p.status for p in s.query(D.Page)}
        assert st == {1: "in_review", 2: "failed"}
    assert work(env, StubEngine())[0] == "succeeded"       # page 1 is NOT reprocessed
    with env.sf() as s:
        assert s.query(D.ProcessingRun).filter_by(page_id=s.query(D.Page).filter_by(page_no=1).one().id,
                                                  status="succeeded").count() == 1


def test_missing_source_linkage_fails_validation_but_keeps_raw_output(env):
    upload(env, png_bytes())
    work(env, StubEngine(bad_linkage=True), 3)
    with env.sf() as s:
        runs = s.query(D.ProcessingRun).all()
        assert all(r.status == "failed_validation" for r in runs) and runs[0].raw_output_path
        assert s.query(D.PageVersion).count() == 0         # nothing unlinked enters the canonical store


def test_engine_unavailable_blocks_without_burning_retries(env):
    class Down(StubEngine):
        def recognize(self, *a, **k): raise EngineUnavailable("no GPU / weights")
    upload(env, png_bytes())
    assert work(env, Down())[0] == "blocked"
    with env.sf() as s:
        j = s.query(D.Job).one(); assert j.status == "blocked" and j.attempts == 0


def test_canonical_model_rejects_bad_geometry_and_empty_recognized():
    with pytest.raises(ValidationError):
        Region(region_id="a", label="text", bbox=[10, 10, 5, 5], text="x")
    with pytest.raises(ValidationError):
        Region(region_id="a", label="text", bbox=[0, 0, 5, 5], text="", status="recognized")
    with pytest.raises(ValidationError):
        CanonicalPage(page_id="p", page_no=1, width=10, height=10, source_sha256="0" * 64,
                      regions=[Region(region_id="a", label="text", bbox=[0, 0, 50, 5], text="x")])


# ---------- review / approval / export ----------
def processed(env):
    doc = upload(env, png_bytes()).json()["document_id"]; work(env)
    return doc, first_page(env, doc)


def test_concurrent_review_edits_second_writer_gets_409(env):
    _, pid = processed(env)
    body = {"base_version_no": 1, "edits": [{"region_id": "r2", "text": "تعديل أ"}], "reason": "typo"}
    a = env.client.put(f"/api/v1/pages/{pid}/draft", headers=H("demo-reviewer1"), json=body)
    b = env.client.put(f"/api/v1/pages/{pid}/draft", headers=H("demo-reviewer2"),
                       json={**body, "edits": [{"region_id": "r2", "text": "تعديل ب"}]})
    assert a.status_code == 200 and b.status_code == 409


def test_save_is_not_approve_and_raw_text_is_never_overwritten(env):
    _, pid = processed(env)
    env.client.put(f"/api/v1/pages/{pid}/draft", headers=H("demo-reviewer1"),
                   json={"base_version_no": 1, "edits": [{"region_id": "r2", "text": "نص مصحح"}], "reason": "r"})
    j = env.client.get(f"/api/v1/pages/{pid}/content", headers=H("demo-reviewer1")).json()
    assert j["kind"] == "draft" and j["page_status"] != "approved"
    with env.sf() as s:
        raw = s.query(D.PageVersion).filter_by(page_id=pid, version_no=1).one()
        assert raw.kind == "raw" and "TEST-FIXTURE" in raw.content["regions"][1]["text"]
        c = s.query(D.Correction).one(); assert c.old_text.startswith("[TEST-FIXTURE") and c.new_text == "نص مصحح"


def test_approval_then_reopen_preserves_previous_approved_version(env):
    _, pid = processed(env)
    ok = env.client.post(f"/api/v1/pages/{pid}/approve", headers=H("demo-reviewer1"), json={"version_no": 1})
    assert ok.status_code == 200 and ok.json()["version_no"] == 2
    assert env.client.put(f"/api/v1/pages/{pid}/draft", headers=H("demo-reviewer1"),
                          json={"base_version_no": 2, "edits": [{"region_id": "r2", "text": "x"}]}).status_code == 409
    assert env.client.post(f"/api/v1/pages/{pid}/reopen", headers=H("demo-reviewer1"),
                           json={"reason": "r"}).status_code == 403          # reviewer cannot reopen
    assert env.client.post(f"/api/v1/pages/{pid}/reopen", headers=H("demo-supervisor"),
                           json={"reason": "fix"}).status_code == 200
    with env.sf() as s:
        kinds = [(v.version_no, v.kind) for v in s.query(D.PageVersion).filter_by(page_id=pid).order_by(D.PageVersion.version_no)]
        assert kinds == [(1, "raw"), (2, "approved"), (3, "draft")]           # approved row still there, untouched


def test_unresolved_uncertain_region_blocks_approval(env):
    _, pid = processed(env)
    env.client.put(f"/api/v1/pages/{pid}/draft", headers=H("demo-reviewer1"),
                   json={"base_version_no": 1, "edits": [{"region_id": "r2", "status": "uncertain"}]})
    r = env.client.post(f"/api/v1/pages/{pid}/approve", headers=H("demo-reviewer1"), json={"version_no": 2})
    assert r.status_code == 422


def test_schema_validation_failure_rejects_export_without_partial_delivery(env):
    doc, pid = processed(env)
    assert env.client.post(f"/api/v1/documents/{doc}/export", headers=H("demo-supervisor")).json()["status"] == "rejected"  # unapproved
    env.client.post(f"/api/v1/pages/{pid}/approve", headers=H("demo-reviewer1"), json={"version_no": 1})
    import json, pathlib
    bad = pathlib.Path(env.cfg.data_dir) / "strict.json"
    bad.write_text(json.dumps({"type": "object", "required": ["case_number"], "title": "strict", "$comment": "t"}))
    from sanad import export as X
    from sanad.auth import principal_from_token
    with env.sf() as s:
        rec = X.export_document(s, principal_from_token(env.cfg.users, "demo-supervisor"), doc, bad)
        assert rec.status == "rejected" and "case_number" in rec.errors[0] and rec.payload is None; s.commit()
    ok = env.client.post(f"/api/v1/documents/{doc}/export", headers=H("demo-supervisor")).json()
    assert ok["status"] == "delivered" and ok["payload"]["demo_only"] is False   # injected test worker is not a legacy synthetic record


def test_mock_content_cannot_be_approved_or_exported_in_secure_mode(env):
    _, pid = processed(env)
    with env.sf() as session:
        session.query(D.PageVersion).filter_by(page_id=pid).one().is_mock = True
        session.commit()
    from sanad import review as R
    from sanad.auth import principal_from_token
    with env.sf() as s, pytest.raises(R.Invalid):
        R.approve(s, principal_from_token(env.cfg.users, "demo-reviewer1"), pid, 1)


# ---------- authorization / audit ----------
def test_unauthorized_access_404_across_orgs_403_by_role(env):
    doc, pid = processed(env)
    for url in (f"/api/v1/documents/{doc}", f"/api/v1/pages/{pid}/content", f"/api/v1/pages/{pid}/image"):
        assert env.client.get(url, headers=H("demo-other-org")).status_code == 404
        assert env.client.get(url, headers=H("demo-admin")).status_code == 403      # admin has no content permission
        assert env.client.get(url).status_code == 401
    assert env.client.put(f"/api/v1/pages/{pid}/draft", headers=H("demo-other-org"),
                          json={"base_version_no": 1, "edits": []}).status_code == 404
    assert env.client.post("/api/v1/documents", headers=H("demo-other-org"), data={"org_scope": "demo-court-a"},
                           files={"file": ("a.png", png_bytes(mark=7))}).status_code == 403


def test_audit_chain_detects_tampering(env):
    processed(env)
    assert env.client.get("/api/v1/audit/verify", headers=H("demo-admin")).json()["intact"] is True
    with env.sf() as s:
        e = s.query(D.AuditEvent).first(); e.actor = "mallory"; s.commit()
    assert env.client.get("/api/v1/audit/verify", headers=H("demo-admin")).json()["intact"] is False


def test_health_endpoints_and_secure_mode_refuses_demo_auth(env, monkeypatch):
    assert env.client.get("/healthz").json()["external_processing"] is False
    assert env.client.get("/readyz").status_code == 200
    from sanad.config import Settings
    monkeypatch.setenv("SANAD_ENV", "secure"); monkeypatch.delenv("SANAD_USERS_FILE", raising=False)
    with pytest.raises(RuntimeError):
        Settings.from_env()

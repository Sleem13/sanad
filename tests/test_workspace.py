import json

from conftest import H, png_bytes, upload, work


def test_ocr_disagreement_survives_pipeline_and_blocks_approval(env):
    from fakes import StubEngine

    class DisagreeingEngine(StubEngine):
        def recognize(self, *args, **kwargs):
            result = super().recognize(*args, **kwargs)
            result.regions[1].extra = {"flags": ["ocr_disagreement"],
                                       "requires_review": True, "alternatives": ["قراءة أخرى"]}
            return result

    doc = upload(env, png_bytes()).json()["document_id"]
    work(env, DisagreeingEngine())
    detail = env.client.get(f"/api/v1/documents/{doc}", headers=H("demo-reviewer1")).json()
    pid = detail["pages"][0]["id"]
    content = env.client.get(f"/api/v1/pages/{pid}/content", headers=H("demo-reviewer1")).json()
    region = content["content"]["regions"][1]
    assert region["status"] == "requires_review" and region["alternatives"] == ["قراءة أخرى"]
    assert env.client.post(f"/api/v1/pages/{pid}/approve", headers=H("demo-reviewer1"),
                           json={"version_no": 1}).status_code == 422


def test_local_super_admin_opens_without_tokens_and_controls_full_workflow(env):
    from fastapi.testclient import TestClient
    client = TestClient(env.app, client=("127.0.0.1", 51000))
    assert client.get("/api/v1/me").status_code == 401
    response = client.post("/api/v1/dev/session")
    assert response.status_code == 200 and "HttpOnly" in response.headers["set-cookie"]
    who = client.get("/api/v1/me").json()
    assert who["roles"] == ["super_admin"] and who["orgs"] == ["*"]
    assert {"ingest", "approve", "export", "read_audit", "assign"} <= set(who["permissions"])
    result = client.post("/api/v1/documents", data={"org_scope": "any-court", "demo": "true"},
                         files={"file": ("admin-demo.png", png_bytes(), "image/png")}).json()
    detail = client.get(f"/api/v1/documents/{result['document_id']}").json()
    work(env)
    pid = detail["pages"][0]["id"]
    assert client.post(f"/api/v1/pages/{pid}/approve", json={"version_no": 1}).status_code == 200
    assert client.post(f"/api/v1/documents/{result['document_id']}/export").json()["status"] == "delivered"
    assert client.get("/api/v1/audit/verify").json()["intact"] is True
    env.cfg.env = "secure"
    assert client.post("/api/v1/dev/session").status_code == 404
    assert client.get("/api/v1/me").status_code == 401


def test_local_super_admin_session_rejects_remote_and_cross_origin_requests(env):
    from fastapi.testclient import TestClient
    assert env.client.post("/api/v1/dev/session").status_code == 403
    client = TestClient(env.app, client=("127.0.0.1", 51000))
    assert client.post("/api/v1/dev/session", headers={"Origin": "https://other.example"}).status_code == 403
    env.cfg.dev_super_admin = False
    assert client.post("/api/v1/dev/session").status_code == 404


def test_workspace_and_scoped_listing(env):
    doc = upload(env, png_bytes()).json()["document_id"]
    assert env.client.get("/").status_code == 200
    assert env.client.get("/static/workspace.js").status_code == 200
    assert env.client.get("/api/v1/documents").status_code == 401
    assert env.client.get("/api/v1/documents", headers=H("demo-other-org")).json()["items"] == []
    assert env.client.get("/api/v1/documents", headers=H("demo-admin")).status_code == 403
    assert env.client.get("/api/v1/documents", headers=H("demo-operator")).json()["items"][0]["id"] == doc
    assert "ingest" in env.client.get("/api/v1/me", headers=H("demo-operator")).json()["permissions"]


def test_job_controls_are_scoped_and_real_processing_is_explicit(env, monkeypatch):
    from fakes import StubEngine
    monkeypatch.setattr("sanad.engines.paddleocr_arabic.PaddleArabicEngine", StubEngine)
    doc = upload(env, png_bytes()).json()["document_id"]
    details = env.client.get(f"/api/v1/documents/{doc}", headers=H("demo-operator")).json()
    job = details["jobs"][0]["id"]
    route = f"/api/v1/jobs/{job}"
    assert env.client.post(route + "/demo-step", headers=H("demo-operator")).status_code == 404
    assert env.client.post(f"/api/v1/documents/{doc}/recognize", headers=H("demo-other-org")).status_code == 404
    assert env.client.post(f"/api/v1/documents/{doc}/recognize", headers=H("demo-reviewer1")).status_code == 403
    assert env.client.post(route + "/cancel", headers=H("demo-operator")).json()["status"] == "cancelled"
    assert env.client.post(route + "/retry", headers=H("demo-operator")).json()["status"] == "queued"
    response = env.client.post(f"/api/v1/documents/{doc}/recognize", headers=H("demo-operator"))
    assert response.status_code == 202 and response.json()["is_mock"] is False
    env.app.state.worker_thread.join(timeout=5)
    assert not env.app.state.worker_thread.is_alive()
    pid = details["pages"][0]["id"]
    content = env.client.get(f"/api/v1/pages/{pid}/content", headers=H("demo-reviewer1")).json()
    assert content["is_mock"] is False and content["version_no"] == 1
    # A second run creates a new immutable version instead of silently leaving old text visible.
    assert env.client.post(f"/api/v1/documents/{doc}/recognize", headers=H("demo-operator")).status_code == 202
    env.app.state.worker_thread.join(timeout=5)
    assert env.client.get(f"/api/v1/pages/{pid}/content", headers=H("demo-reviewer1")).json()["version_no"] == 2


def test_removed_engine_cannot_be_selected(monkeypatch):
    import pytest
    from sanad.config import Settings
    from sanad.engines.paddleocr_vl import build_engine
    with pytest.raises(ValueError):
        build_engine("mock")
    monkeypatch.setenv("SANAD_ENGINE", "mock")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_legacy_output_cannot_be_approved_even_in_dev(env):
    from sanad import db as D
    doc = upload(env, png_bytes()).json()["document_id"]
    work(env)
    with env.sf() as s:
        version = s.query(D.PageVersion).one()
        version.is_mock = True
        pid = version.page_id
        s.commit()
    assert env.client.post(f"/api/v1/pages/{pid}/approve", headers=H("demo-reviewer1"),
                           json={"version_no": 1}).status_code == 422
    assert env.client.post(f"/api/v1/documents/{doc}/export", headers=H("demo-supervisor")).json()["status"] == "rejected"


def test_arabic_raw_output_uses_utf8_and_inference_releases_database_lock(env, monkeypatch):
    from pathlib import Path
    from fakes import StubEngine
    from sanad import db as D
    original = Path.write_text

    def windows_default(path, data, encoding=None, **kwargs):
        # Reproduce the locale-dependent Windows failure on every test platform.
        return original(path, data, encoding=encoding or "cp1252", **kwargs)

    class ArabicEngine(StubEngine):
        def recognize(self, *args, **kwargs):
            # A second writer must be able to commit while native inference runs.
            with env.sf() as other:
                D.audit(other, "test", "inference.concurrent_write", "test", "utf8")
                other.commit()
            result = super().recognize(*args, **kwargs)
            result.raw = {"text": "نص عربي ١٢٣ مع التشكيل مُراجَع"}
            result.regions[1].text = result.raw["text"]
            return result

    monkeypatch.setattr(Path, "write_text", windows_default)
    upload(env, png_bytes())
    assert work(env, ArabicEngine())[0] == "succeeded"
    raw_file = next((env.cfg.data_dir / "raw_outputs").glob("*.json"))
    assert json.loads(raw_file.read_bytes().decode("utf-8"))["text"] == "نص عربي ١٢٣ مع التشكيل مُراجَع"


def test_public_review_preserves_source_and_rejects_stale_edits(env):
    root = env.cfg.data_dir / "research" / "egyptian-eval"
    (root / "images").mkdir(parents=True)
    (root / "images" / "a.png").write_bytes(png_bytes())
    source = dict(id="example", document_id="public:one", split="test", image="images/a.png",
                  text="نص", reviewed=False, source_page=1, review_notes=[])
    path = root / "pending_review.jsonl"
    path.write_text(json.dumps(source), encoding="utf-8")
    route = "/api/v1/dataset/example/review"
    body = dict(text="نص مراجع", note="Checked fixture", base_revision=0, checked_against_image=False)
    assert env.client.put(route, headers=H("demo-reviewer1"), json=body).status_code == 422
    body["checked_against_image"] = True
    assert env.client.put(route, headers=H("demo-operator"), json=body).status_code == 403
    assert env.client.put(route, headers=H("demo-reviewer1"), json=body).status_code == 200
    assert env.client.put(route, headers=H("demo-reviewer1"), json=body).status_code == 409
    assert json.loads(path.read_text(encoding="utf-8")) == source
    saved = json.loads((root / "reviewed.jsonl").read_text(encoding="utf-8"))
    assert saved["reviewed_by"] == "demo.reviewer1" and saved["review_history"][0]["previous_text"] == "نص"
    assert env.client.get("/api/v1/dataset/example/image", headers=H("demo-reviewer1")).status_code == 200


def test_assign_and_escalation_are_connected(env):
    doc = upload(env, png_bytes()).json()["document_id"]
    detail = env.client.get(f"/api/v1/documents/{doc}", headers=H("demo-operator")).json()
    work(env)
    route = f"/api/v1/pages/{detail['pages'][0]['id']}"
    assert env.client.post(route + "/assign", headers=H("demo-supervisor"), json={"assignee": "demo.other"}).status_code == 422
    assert env.client.post(route + "/assign", headers=H("demo-supervisor"), json={"assignee": "demo.reviewer1"}).status_code == 200
    assert env.client.post(route + "/escalate", headers=H("demo-reviewer1"), json={"note": "Unreadable number"}).status_code == 200

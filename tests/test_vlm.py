from conftest import H, upload, png_bytes, work, first_page
from sanad.understanding import validate_fields


def test_engine_comparison_preserves_vlm_text_and_records_source():
    from sanad.engines.base import RawRegion
    from sanad.engines.comparison import attach_comparison
    region = RawRegion("text", [0,0,100,40], "نص VLM", 0)
    baseline = [{"bbox":[2,2,90,15], "text":"نص OCR", "reading_order":0}]
    attach_comparison([region], baseline, "paddleocr_arabic:v2")
    assert region.text == "نص VLM"
    assert region.extra["alternatives"] == ["نص OCR"]
    assert region.extra["alternative_sources"] == ["paddleocr_arabic:v2"]
    assert region.extra["requires_review"]


def test_table_structure_preserves_spans_without_executing_markup():
    from sanad.table_structure import table_cells
    cells = table_cells('<table><tr><th rowspan="2">اسم</th><td>٣٥</td></tr><tr><td>نص &amp; نص</td></tr></table>')
    assert len(cells) == 3
    assert cells[0]["rowspan"] == 2 and cells[2]["col"] == 1
    assert cells[2]["text"] == "نص & نص"
    assert table_cells('<table><tr><td rowspan="bad">نص</td></tr></table>') is None


def test_training_export_excludes_unapproved_and_unresolved_pages(env, tmp_path, monkeypatch):
    import json
    import runpy
    from pathlib import Path
    from sanad.config import Settings
    exporter = runpy.run_path(str(Path(__file__).parents[1]/"scripts/export_approved_dataset.py"))["export"]
    monkeypatch.setattr(Settings, "from_env", lambda: env.cfg)
    doc = upload(env, png_bytes()).json()["document_id"]
    work(env); pid = first_page(env, doc)
    upload(env, png_bytes(mark=1))
    assert env.client.post(f"/api/v1/pages/{pid}/approve", headers=H("demo-reviewer1"), json={"version_no":1}).status_code == 200
    output = tmp_path/"export"
    exporter(output)
    rows = [json.loads(line) for line in (output/"manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1 and rows[0]["reviewed"] and rows[0]["approved_version_id"]
    assert (output/rows[0]["image"]).is_file()


def test_grounding_rejects_hallucinated_names_dates_and_unknown_regions():
    page = {"regions": [{"region_id": "r1", "text": "المكتب الفني ١٧٢", "bbox": [1,2,30,40]}]}
    proposal = {"fields": [
        {"kind": "title", "value": "المكتب الفني", "region_ids": ["r1"]},
        {"kind": "date", "value": "٢٠٢٣/٨/٢", "region_ids": ["r1"]},
        {"kind": "reference_number", "value": "172", "region_ids": ["r1"]},
        {"kind": "person", "value": "المكتب الفني", "region_ids": ["invented"]}]}
    result = validate_fields(proposal, page)
    assert len(result["fields"]) == 1 and len(result["rejected"]) == 3
    assert result["fields"][0]["bboxes"] == [[1,2,30,40]]
    assert result["fields"][0]["requires_review"]


def test_model_controls_require_admin_and_missing_assets_are_explicit(env):
    assert env.client.get("/api/v1/models/runtime").status_code == 401
    assert env.client.post("/api/v1/models/start", headers=H("demo-operator")).status_code == 403
    status = env.client.get("/api/v1/models/runtime", headers=H("demo-admin")).json()
    assert status["state"] == "not_provisioned"
    assert env.client.post("/api/v1/models/start", headers=H("demo-admin")).status_code == 422


def test_vlm_selection_is_real_and_scope_checked(env, monkeypatch):
    from fakes import StubEngine
    class VL(StubEngine):
        engine_id = "paddleocr_vl"
        def __init__(self, *args, **kwargs):
            super().__init__()
    doc = upload(env, png_bytes()).json()["document_id"]
    route = f"/api/v1/documents/{doc}/recognize"
    assert env.client.post(route, headers=H("demo-other-org"), json={"engine":"paddleocr_vl"}).status_code == 404
    assert env.client.post(route, headers=H("demo-operator"), json={"engine":"mock"}).status_code == 422
    assert env.client.post(route, headers=H("demo-operator"), json={"engine":"paddleocr_vl"}).status_code == 422
    monkeypatch.setattr(env.app.state.vlm, "status", lambda: {"state":"ready"})
    monkeypatch.setattr("sanad.engines.local_vlm.LocalVLMEngine", VL)
    result = env.client.post(route, headers=H("demo-operator"), json={"engine":"paddleocr_vl"})
    assert result.status_code == 202 and result.json()["engine"] == "paddleocr_vl"
    env.app.state.worker_thread.join(5)
    detail = env.client.get(f"/api/v1/documents/{doc}", headers=H("demo-operator")).json()
    assert any(j["engine"] == "paddleocr_vl" and j["status"] == "succeeded" for j in detail["jobs"])


def test_understanding_is_scoped_and_bound_to_saved_version(env, monkeypatch):
    from unittest.mock import MagicMock
    from sanad import db as D
    doc = upload(env, png_bytes()).json()["document_id"]
    work(env); pid = first_page(env, doc)
    route = f"/api/v1/pages/{pid}/understanding"
    assert env.client.post(route, headers=H("demo-operator")).status_code == 403
    response = MagicMock()
    response.__enter__.return_value.read.return_value = b'{"models":[{"name":"gemma3:4b"}]}'
    monkeypatch.setattr("sanad.vlm_api.urlopen", lambda *args, **kw: response)
    monkeypatch.setattr("sanad.understanding.extract", lambda page: {"fields":[], "review_required":True})
    assert env.client.post(route, headers=H("demo-reviewer1")).status_code == 202
    env.app.state.understanding_thread.join(5)
    assert env.client.get(route, headers=H("demo-reviewer1")).json()["status"] == "succeeded"
    assert env.client.get(route, headers=H("demo-other-org")).status_code == 404
    saved = env.client.put(f"/api/v1/pages/{pid}/draft", headers=H("demo-reviewer1"), json={"base_version_no":1,"edits":[{"region_id":"r2","text":"نص جديد"}]})
    assert saved.status_code == 200
    assert env.client.get(route, headers=H("demo-reviewer1")).json()["status"] == "not_processed"

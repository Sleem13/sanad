import base64
import io
import json
from unittest.mock import MagicMock

import pytest
from PIL import Image

from conftest import H, upload, png_bytes
from sanad.engines.base import EngineUnavailable
from sanad.engines.full_page_vlm import FullPageVLMEngine


def test_repeated_hallucination_is_rejected(tmp_path, monkeypatch):
    source = tmp_path / "image.png"
    Image.new("RGB", (10, 10)).save(source)
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps({"choices": [
        {"message": {"content": "+100LOTS\n" * 23}, "finish_reason": "stop"}]}).encode()
    monkeypatch.setattr("sanad.engines.full_page_vlm.urlopen", lambda *a, **kw: response)
    with pytest.raises(EngineUnavailable, match="repetitive generation"):
        FullPageVLMEngine().recognize(source, 10, 10)


def test_blank_margin_crop_preserves_document_offsets():
    from PIL import ImageDraw
    from sanad.engines.full_page_vlm import prepare_page
    image = Image.new("RGB", (780, 440), "white")
    ImageDraw.Draw(image).rectangle((230, 0, 542, 439), fill=(140, 140, 140))
    prepared, meta = prepare_page(image)
    assert meta["crop_bbox"] == [224, 0, 549, 440]
    assert prepared.size == (650, 880)


def test_full_page_preserves_frame_and_marks_coarse_truncated_output(tmp_path, monkeypatch):
    source = tmp_path / "original"
    Image.new("RGB", (50, 60), "white").save(source, format="TIFF", save_all=True,
        append_images=[Image.new("RGB", (50, 60), "red")])
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps({"choices": [
        {"message": {"content": "نص الصفحة الثانية"}, "finish_reason": "length"}]}).encode()
    requests = []
    def serve(request, timeout):
        requests.append(request)
        assert timeout == 1800
        return response
    monkeypatch.setattr("sanad.engines.full_page_vlm.urlopen", serve)
    engine = FullPageVLMEngine(api_key="private")
    result = engine.recognize(source, 50, 60, page_no=2)
    sent = json.loads(requests[0].data)
    encoded = sent["messages"][0]["content"][1]["image_url"]["url"].split(",", 1)[1]
    assert Image.open(io.BytesIO(base64.b64decode(encoded))).getpixel((0, 0)) == (255, 0, 0)
    region = result.regions[0]
    assert region.text == "نص الصفحة الثانية" and region.bbox == [0, 0, 50, 60]
    assert region.extra["requires_review"]
    assert {"whole_page_only", "generation_truncated"} <= set(region.extra["flags"])
    assert region.engine_score is None and engine.config()["layout"] == "none"


@pytest.mark.parametrize("choice", [None, {"message": {"content": ""}, "finish_reason": "stop"},
    {"message": {"content": "text"}, "finish_reason": "error"}])
def test_invalid_or_empty_responses_are_blocked(tmp_path, monkeypatch, choice):
    source = tmp_path / "image.png"
    Image.new("RGB", (10, 10)).save(source)
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps({"choices": [choice]}).encode()
    monkeypatch.setattr("sanad.engines.full_page_vlm.urlopen", lambda *a, **kw: response)
    with pytest.raises(EngineUnavailable):
        FullPageVLMEngine().recognize(source, 10, 10)


def test_full_page_route_keeps_scope_and_review_requirements(env, monkeypatch):
    from sanad.engines.base import EngineResult, RawRegion
    doc = upload(env, png_bytes()).json()["document_id"]
    route = f"/api/v1/documents/{doc}/recognize"
    body = {"engine": "paddleocr_vl_full_page"}
    assert env.client.post(route, headers=H("demo-other-org"), json=body).status_code == 404
    assert env.client.post(route, headers=H("demo-operator"), json=body).status_code == 422
    monkeypatch.setattr(env.app.state.vlm, "status", lambda: {"state": "ready"})
    monkeypatch.setattr(FullPageVLMEngine, "recognize", lambda *a, **kw: EngineResult([
        RawRegion("text", [0, 0, 400, 600], "نص", 0,
                  extra={"requires_review": True, "flags": ["whole_page_only"]})], {}))
    assert env.client.post(route, headers=H("demo-operator"), json=body).status_code == 202
    env.app.state.worker_thread.join(5)
    detail = env.client.get(f"/api/v1/documents/{doc}", headers=H("demo-operator")).json()
    assert any(j["engine"] == body["engine"] and j["status"] == "succeeded" for j in detail["jobs"])
    page = detail["pages"][0]["id"]
    content = env.client.get(f"/api/v1/pages/{page}/content", headers=H("demo-operator")).json()
    assert content["content"]["regions"][0]["status"] == "requires_review"

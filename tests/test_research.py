import json

import pytest

from sanad.research import load_manifest, score


def test_error_counts_and_empty_reference():
    result = score([("abc", "axbc"), ("", "z")])
    assert result["raw_cer"] == {"errors": 2, "reference_units": 3, "rate": 2 / 3}
    assert result["raw_wer"]["errors"] == 2
    assert score([("", "x")])["raw_cer"]["rate"] is None


def test_nfc_is_separate_and_digits_are_preserved():
    result = score([("أ١", "ا\u0654١")])
    assert result["raw_cer"]["errors"] > 0
    assert result["nfc_cer"]["errors"] == 0
    assert score([("١", "1")])["nfc_cer"]["errors"] == 1


@pytest.mark.parametrize("same_document,same_image", [(True, False), (False, True)])
def test_manifest_rejects_split_leakage(tmp_path, same_document, same_image):
    (tmp_path / "a.png").write_bytes(b"a")
    (tmp_path / "b.png").write_bytes(b"b")
    rows = [dict(id="a", document_id="doc", split="train", image="a.png", text="", reviewed=True),
            dict(id="b", document_id="doc" if same_document else "other", split="test",
                 image="a.png" if same_image else "b.png", text="", reviewed=True)]
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text("\n".join(json.dumps(r) for r in rows))
    with pytest.raises(ValueError, match="leaks"):
        load_manifest(manifest)


def test_manifest_requires_review_and_resolves_relative_images(tmp_path):
    (tmp_path / "a.png").write_bytes(b"a")
    row = dict(id="a", document_id="doc", split="dev", image="a.png", text="", reviewed=False)
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(json.dumps(row))
    with pytest.raises(ValueError, match="reviewed"):
        load_manifest(manifest)
    row["reviewed"] = True
    manifest.write_text(json.dumps(row))
    assert load_manifest(manifest)[0]["image"] == str((tmp_path / "a.png").resolve())


def test_runner_records_predictions_metrics_and_refuses_overwrite(tmp_path, monkeypatch):
    from sanad import research
    (tmp_path / "a.png").write_bytes(b"test fixture; backend is replaced")
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(json.dumps(dict(id="a", document_id="doc", split="dev", image="a.png",
                                       text="نص", reviewed=True)), encoding="utf-8")
    output = tmp_path / "result.jsonl"

    class FakeGemma:
        def __init__(self, *args):
            self.metadata = {"model": "test-double"}

        def predict(self, path):
            return {"text": "نص", "raw_output": "نص", "token_limit_reached": False}

    monkeypatch.setattr(research, "LocalGemma", FakeGemma)
    monkeypatch.setattr("sys.argv", ["research", str(manifest), "--engine", "gemma", "--model-dir",
                                   str(tmp_path), "--revision", "fixture", "--output", str(output)])
    research.main()
    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert [r["type"] for r in records] == ["run", "prediction", "metrics"]
    assert records[-1]["raw_cer"]["rate"] == 0
    with pytest.raises(FileExistsError):
        research.main()

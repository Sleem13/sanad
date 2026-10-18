"""Executed with the existing Paddle Python environment; JSON output goes to a private file."""
import json
import os
import sys
from pathlib import Path

# The supplied environment was moved with its source archive; its editable-install
# pointer can still reference the old checkout. Use the provided checkout explicitly.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "PaddleOCR-main"))

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"


def main():
    import importlib.metadata
    import numpy as np
    from PIL import Image
    from paddleocr import PaddleOCR
    from image_preparation import prepare, original_polygon, merge_readings

    source, target, models = map(Path, sys.argv[1:4])
    pipeline = PaddleOCR(
        text_detection_model_name="PP-OCRv5_server_det",
        text_detection_model_dir=str(models / "PP-OCRv5_server_det"),
        text_recognition_model_name="arabic_PP-OCRv5_mobile_rec",
        text_recognition_model_dir=str(models / "arabic_PP-OCRv5_mobile_rec"),
        device="cpu", use_doc_orientation_classify=False, use_doc_unwarping=False,
        use_textline_orientation=False, text_rec_score_thresh=0.0,
        enable_mkldnn=False, cpu_threads=4,
    )
    quality = sys.argv[4] if len(sys.argv) > 4 else "balanced"
    if quality not in {"balanced", "baseline"}:
        raise ValueError("unknown quality profile")
    profiles = ["illumination", "contrast"] if quality == "balanced" else ["baseline"]
    with Image.open(source) as image:
        original = image.convert("RGB")
    readings, preparation = [], []
    for profile in profiles:
        working, metadata = prepare(original, profile, resize_backend="opencv")
        preparation.append(metadata)
        pixels = np.asarray(working)[:, :, ::-1].copy()
        result = next(iter(pipeline.predict(pixels, text_det_limit_side_len=1280, text_det_limit_type="max")))
        texts, scores, polygons = result["rec_texts"], result["rec_scores"], result["rec_polys"]
        if not (len(texts) == len(scores) == len(polygons)):
            raise ValueError("inconsistent OCR line arrays")
        readings.append([{"text": str(t), "score": float(s), "profile": profile,
                          "polygon": original_polygon(np.asarray(p).tolist(), metadata)}
                         for t, s, p in zip(texts, scores, polygons)])
    lines = merge_readings(readings[0], readings[1] if len(readings) > 1 else [])
    payload = {"engine": "paddleocr_arabic", "is_mock": False,
               "paddleocr_version": importlib.metadata.version("paddleocr"),
               "recognizer": "arabic_PP-OCRv5_mobile_rec", "quality": quality,
               "preparation": preparation, "candidate_readings": readings, "lines": lines}
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()

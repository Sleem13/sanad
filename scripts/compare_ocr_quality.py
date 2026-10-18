"""Local, private OCR experiment. Does not modify originals or approved page versions."""
import json
import os
import sys
from pathlib import Path

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "PaddleOCR-main"))


def main():
    import cv2
    import numpy as np
    from PIL import Image
    from paddleocr import PaddleOCR

    models = Path.home() / ".paddlex" / "official_models"
    engine = PaddleOCR(text_detection_model_name="PP-OCRv5_server_det",
                       text_detection_model_dir=str(models / "PP-OCRv5_server_det"),
                       text_recognition_model_name="arabic_PP-OCRv5_mobile_rec",
                       text_recognition_model_dir=str(models / "arabic_PP-OCRv5_mobile_rec"),
                       device="cpu", use_doc_orientation_classify=False, use_doc_unwarping=False,
                       use_textline_orientation=False, text_rec_score_thresh=0.0,
                       enable_mkldnn=False, cpu_threads=4)
    profiles = ["upscale", "illumination", "contrast"]
    for source in sys.argv[1:]:
        path = Path(source)
        with Image.open(path) as image:
            original = np.asarray(image.convert("RGB"))[:, :, ::-1].copy()
        scale = max(1.0, min(4.0, 1200 / max(original.shape[:2])))
        enlarged = cv2.resize(original, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        for name in profiles:
            pixels = enlarged.copy()
            if name == "illumination":
                gray = cv2.cvtColor(pixels, cv2.COLOR_BGR2GRAY)
                background = cv2.GaussianBlur(gray, (0, 0), 25)
                gray = cv2.divide(gray, np.maximum(background, 1), scale=235)
                pixels = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            elif name == "contrast":
                lab = cv2.cvtColor(pixels, cv2.COLOR_BGR2LAB)
                lab[:, :, 0] = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(lab[:, :, 0])
                pixels = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            result = next(iter(engine.predict(pixels, text_det_limit_side_len=1280, text_det_limit_type="max")))
            payload = {"source": str(path), "profile": name, "scale": scale, "lines": [
                {"text": str(text), "score": float(score), "polygon": (np.asarray(poly) / scale).tolist()}
                for text, score, poly in zip(result["rec_texts"], result["rec_scores"], result["rec_polys"])]}
            output = Path("data/research/ocr_quality") / f"{path.name[:12]}-{name}.json"
            output.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            print(f"saved {name}: {len(payload['lines'])} lines", flush=True)


if __name__ == "__main__":
    main()

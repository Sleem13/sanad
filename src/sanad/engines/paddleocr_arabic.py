"""Use the provided, installed Arabic PP-OCRv5 CPU runtime without mixing Python environments."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

from .base import EngineResult, EngineUnavailable, RawRegion


class PaddleArabicEngine:
    engine_id = "paddleocr_arabic"
    is_mock = False

    def __init__(self, python_path=None, models_dir=None, quality=None):
        root = Path(__file__).resolve().parents[3]
        self.python = Path(python_path or os.getenv("SANAD_PADDLE_PYTHON", "") or
                           root / "PaddleOCR-main" / ".venv" / "Scripts" / "python.exe")
        self.models = Path(models_dir or os.getenv("SANAD_PADDLE_MODELS", "") or
                           Path.home() / ".paddlex" / "official_models")
        self.quality = quality or os.getenv("SANAD_OCR_QUALITY", "balanced")
        if self.quality not in {"balanced", "baseline"}:
            raise ValueError("unknown OCR quality profile")
        self._version = f"PP-OCRv5;arabic_PP-OCRv5_mobile_rec;quality={self.quality}-v1"

    def version(self):
        return self._version

    def config(self):
        return {"recognizer": "arabic_PP-OCRv5_mobile_rec", "detector": "PP-OCRv5_server_det",
                "device": "cpu", "cpu_threads": 4, "enable_mkldnn": False,
                "orientation": False, "unwarping": False, "detection_limit": 1280,
                "quality": self.quality, "target_side": 1200, "review_score_threshold": .8}

    def recognize(self, image_path, width, height, page_no=1):
        if not self.python.is_file():
            raise EngineUnavailable("Paddle Python runtime not found; configure SANAD_PADDLE_PYTHON")
        for name in ("PP-OCRv5_server_det", "arabic_PP-OCRv5_mobile_rec"):
            if not (self.models / name / "inference.pdiparams").is_file():
                raise EngineUnavailable(f"local model weights missing: {name}")
        with tempfile.TemporaryDirectory(prefix="sanad-ocr-") as folder:
            target = Path(folder) / "result.json"
            runner = Path(__file__).with_name("paddleocr_arabic_runner.py")
            try:
                completed = subprocess.run([str(self.python), str(runner), str(Path(image_path).resolve()),
                                            str(target), str(self.models.resolve()), self.quality],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600,
                                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            except subprocess.TimeoutExpired as exc:
                raise EngineUnavailable("Paddle OCR timed out on CPU") from exc
            if completed.returncode or not target.exists():
                # Model diagnostics only; do not include document transcriptions in public errors.
                raise EngineUnavailable("Paddle OCR runtime failed; inspect the installed Paddle environment")
            data = json.loads(target.read_text(encoding="utf-8"))
        regions = []
        for i, line in enumerate(data["lines"]):
            points = line["polygon"]
            xs, ys = zip(*points)
            flags = list(line.get("flags", []))
            if line["score"] < 0.8:
                flags.append("low_ocr_score")
            if min(width, height) < 600:
                flags.append("low_resolution_source")
            regions.append(RawRegion("text", [min(xs), min(ys), max(xs), max(ys)], line["text"], i,
                                     engine_score=line["score"], engine_score_kind="paddle_recognition_score",
                                     polygon=points, extra={"flags": sorted(set(flags)),
                                         "requires_review": line.get("requires_review", line["score"] < .8),
                                         "alternatives": [candidate["text"] for candidate in line.get("alternatives", [])
                                                          if candidate["text"] != line["text"]]}))
        return EngineResult(regions, data)

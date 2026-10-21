"""Explicit whole-page VLM recognition without Paddle layout detection."""
import base64
import io
import json
import os
from collections import Counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

from .base import EngineResult, EngineUnavailable, RawRegion


def repetitive(text):
    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    if lines and max(Counter(lines).values()) >= max(4, len(lines) * .6):
        return True
    words = text.split()
    triples = Counter(tuple(words[i:i+3]) for i in range(max(0, len(words)-2)))
    return bool(triples and max(triples.values()) >= 8)


def prepare_page(image):
    """Remove only uniform near-white outer rows/columns, retaining source offsets."""
    gray = image.convert("L")
    # Count dark pixels along each axis; ignore isolated JPEG speckles. This
    # removes blank screenshot margins, not white space inside the document.
    mask = gray.point(lambda value: 255 if value < 235 else 0)
    xs = [i for i, value in enumerate(mask.resize((image.width, 1), Image.Resampling.BOX).getdata()) if value > 5]
    ys = [i for i, value in enumerate(mask.resize((1, image.height), Image.Resampling.BOX).getdata()) if value > 5]
    box = (0, 0, image.width, image.height)
    if xs and ys:
        candidate = (max(0, int(xs[0])-6), max(0, int(ys[0])-6),
                     min(image.width, int(xs[-1])+7), min(image.height, int(ys[-1])+7))
        if (candidate[2]-candidate[0]) * (candidate[3]-candidate[1]) >= image.width*image.height*.2:
            box = candidate
    working = ImageOps.autocontrast(image.crop(box), cutoff=0)
    # Upscaling helps model sampling; it cannot restore missing source detail.
    scale = min(2., 1200 / max(working.size))
    if scale > 1:
        working = working.resize(tuple(round(n*scale) for n in working.size), Image.Resampling.LANCZOS)
    return working, {"crop_bbox": list(box), "input_size": list(working.size),
                     "source_size": list(image.size), "autocontrast": True}


class FullPageVLMEngine:
    engine_id = "paddleocr_vl_full_page"
    is_mock = False

    def __init__(self, data_dir="data", api_key=None):
        self.api_key = api_key or os.getenv("SANAD_VLM_INTERNAL_KEY", "")

    def version(self):
        return "PaddleOCR-VL-1.6;GGUF@511b09642bb324401f15f97cc23bc67e8f0a291d;full-page-v2"

    def config(self):
        return {"device": "cpu", "backend": "llama-cpp-server", "layout": "none",
                "model": "PaddleOCR-VL-1.6-0.9B", "review_required": True,
                "source_coordinates": "whole_page_only", "max_tokens": 2048,
                "prompt": "OCR:", "orientation": False, "unwarping": False,
                "preparation": "outer-white-crop-autocontrast-v1", "repetition_guard": True}

    def recognize(self, image_path, width, height, page_no=1):
        # Explicit TIFF frame selection and PNG encoding also handle extensionless
        # archived originals. No generated line/table coordinates are claimed.
        with Image.open(image_path) as image:
            image.seek(page_no - 1)
            image = image.convert("RGB")
            if image.size != (width, height):
                raise ValueError("source page dimensions do not match")
            image, preparation = prepare_page(image)
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        payload = {"model": "PaddleOCR-VL-1.6-0.9B", "temperature": 0, "max_tokens": 2048,
                   "messages": [{"role": "user", "content": [
                       {"type": "text", "text": "OCR:"},
                       {"type": "image_url", "image_url": {"url": "data:image/png;base64," + encoded}}]}]}
        request = Request("http://127.0.0.1:8111/v1/chat/completions",
                          data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.api_key})
        try:
            with urlopen(request, timeout=1800) as response:
                data = json.load(response)
        except HTTPError as exc:
            raise EngineUnavailable(f"Full-page VLM service returned HTTP {exc.code}") from exc
        except (URLError, TimeoutError) as exc:
            raise EngineUnavailable("Full-page VLM service unavailable or CPU inference exceeded 30 minutes") from exc
        try:
            choice = data["choices"][0]
            text = choice["message"]["content"]
            finish = choice["finish_reason"]
        except (KeyError, IndexError, TypeError) as exc:
            raise EngineUnavailable("Full-page VLM returned an invalid response") from exc
        if not isinstance(text, str) or not text.strip():
            raise EngineUnavailable("Full-page VLM returned no text; review the source image")
        if finish not in {"stop", "length"}:
            raise EngineUnavailable("Full-page VLM did not complete normally")
        if repetitive(text):
            raise EngineUnavailable("VLM output rejected: repetitive generation; source needs a clearer scan or manual transcription")
        flags = ["vlm_needs_review", "whole_page_only"]
        if finish == "length":
            flags.append("generation_truncated")
        box = preparation["crop_bbox"]
        if box[2]-box[0] < 600:
            flags.append("low_resolution_source")
        return EngineResult([RawRegion("text", box, text.strip(), 0,
                            extra={"requires_review": True, "flags": flags})],
                            {"mode": "full_page", "layout": "none", "preparation": preparation, "response": data})

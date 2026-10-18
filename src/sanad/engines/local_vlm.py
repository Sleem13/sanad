"""Full Paddle layout+VLM pipeline in the supplied Paddle environment."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
from .base import EngineUnavailable, EngineResult, RawRegion
from ..table_structure import table_cells


class LocalVLMEngine:
    engine_id = "paddleocr_vl"
    is_mock = False

    def __init__(self, data_dir="data", api_key=None):
        root = Path(__file__).resolve().parents[3]
        self.python = Path(os.getenv("SANAD_PADDLE_PYTHON") or root / "PaddleOCR-main/.venv/Scripts/python.exe")
        self.models = Path(data_dir).resolve() / "models"
        self.api_key = api_key or os.getenv("SANAD_VLM_INTERNAL_KEY", "")

    def version(self):
        return "PaddleOCR-VL-1.6;GGUF@511b09642bb324401f15f97cc23bc67e8f0a291d;layout@241f8bdfc77a7c7bee915a5057aaee58c235a8d3"

    def config(self):
        return {"device": "cpu", "backend": "llama-cpp-server", "layout": "PP-DocLayoutV3",
                "model": "PaddleOCR-VL-1.6-0.9B", "orientation": False, "unwarping": False,
                "source_coordinates": "original", "review_required": True, "block_token_limit": 1024}

    def recognize(self, image_path, width, height, page_no=1):
        if not self.python.is_file() or not (self.models / "layout/inference.pdiparams").is_file():
            raise EngineUnavailable("local VLM runtime or layout weights are missing")
        with tempfile.TemporaryDirectory(prefix="sanad-vlm-") as folder:
            target = Path(folder) / "output.json"
            runner = Path(__file__).with_name("local_vlm_runner.py")
            try:
                result = subprocess.run([str(self.python), str(runner), str(Path(image_path).resolve()),
                    str(target), str(self.models)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    timeout=1800, env={**os.environ, "SANAD_INTERNAL_VLM_KEY": self.api_key},
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            except subprocess.TimeoutExpired as exc:
                raise EngineUnavailable("VLM CPU inference exceeded 30 minutes") from exc
            if result.returncode or not target.exists():
                # Diagnostic file excludes document text and captured model logs.
                reason = "PaddleOCR-VL runtime failed"
                diagnostic = Path(folder) / "error.json"
                if diagnostic.exists():
                    reason += ": " + json.loads(diagnostic.read_text(encoding="utf-8"))["error_type"]
                raise EngineUnavailable(reason)
            data = json.loads(target.read_text(encoding="utf-8"))
        blocks = data.get("parsing_res_list")
        if not isinstance(blocks, list) or not blocks:
            raise EngineUnavailable("VLM returned no source-linked blocks")
        regions = []
        for i, block in enumerate(blocks):
            bbox = block.get("block_bbox")
            if not isinstance(bbox, list) or len(bbox) != 4:
                raise ValueError("VLM block missing source coordinates")
            text = block.get("block_content") or None
            flags = ["vlm_needs_review"]
            if text:
                from collections import Counter
                words = text.split()
                triples = Counter(tuple(words[j:j+3]) for j in range(max(0,len(words)-2)))
                if triples and max(triples.values()) >= 8:
                    flags.append("generation_repetition")
                if len(text) > 2000:
                    flags.append("long_vlm_block")
            regions.append(RawRegion(label=str(block.get("block_label", "text")), bbox=list(map(float,bbox)),
                text=text, reading_order=block.get("block_order") if block.get("block_order") is not None else i,
                extra={"requires_review": True, "flags": flags,
                       "cells": table_cells(text) if block.get("block_label") == "table" else None}))
        return EngineResult(regions, data)

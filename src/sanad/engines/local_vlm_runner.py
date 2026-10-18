"""Runs only in the supplied Paddle environment; model service is loopback-only."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "PaddleOCR-main"))
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"


def main():
    from paddleocr import PaddleOCRVL
    from PIL import Image
    import numpy as np
    source, target, models = map(Path, sys.argv[1:4])
    pipeline = PaddleOCRVL(pipeline_version="v1.6", device="cpu", cpu_threads=4,
        enable_mkldnn=False, layout_detection_model_dir=str(models / "layout"),
        vl_rec_backend="llama-cpp-server", vl_rec_server_url="http://127.0.0.1:8111/v1",
        vl_rec_api_model_name="PaddleOCR-VL-1.6-0.9B", vl_rec_max_concurrency=1,
        vl_rec_api_key=os.getenv("SANAD_INTERNAL_VLM_KEY") or None,
        use_doc_orientation_classify=False, use_doc_unwarping=False, use_seal_recognition=True,
        use_chart_recognition=False, use_queues=False)
    # Archives use extensionless content hashes; upstream file sampling requires
    # image suffixes. Decode ourselves and pass unchanged-size BGR pixels.
    with Image.open(source) as image:
        pixels = np.asarray(image.convert("RGB"))[:, :, ::-1].copy()
    result = next(iter(pipeline.predict(pixels, temperature=0, max_new_tokens=1024)))
    data = result.json
    if isinstance(data, str):
        data = json.loads(data)
    data = data.get("res", data)
    target.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        Path(sys.argv[2]).with_name("error.json").write_text(json.dumps({"error_type": type(exc).__name__}), encoding="utf-8")
        raise

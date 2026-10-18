"""Download pinned official CPU VLM assets; no document is uploaded."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import httpx
import zipfile
import time

ROOT = Path(__file__).resolve().parents[1] / "data" / "models"
ASSETS = {
    "paddle-vl/PaddleOCR-VL-1.6-GGUF.gguf": "https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6-GGUF/resolve/511b09642bb324401f15f97cc23bc67e8f0a291d/PaddleOCR-VL-1.6-GGUF.gguf",
    "paddle-vl/PaddleOCR-VL-1.6-GGUF-mmproj.gguf": "https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6-GGUF/resolve/511b09642bb324401f15f97cc23bc67e8f0a291d/PaddleOCR-VL-1.6-GGUF-mmproj.gguf",
    **{f"layout/{name}": f"https://huggingface.co/PaddlePaddle/PP-DocLayoutV3/resolve/241f8bdfc77a7c7bee915a5057aaee58c235a8d3/{name}"
       for name in ["inference.json", "inference.yml", "inference.pdiparams"]},
    "llama.zip": "https://github.com/ggml-org/llama.cpp/releases/download/b11717/llama-b11717-bin-win-cpu-x64.zip",
}
LARGE = {
    "PaddleOCR-VL-1.6-GGUF.gguf": (935769056, "f3ae46ec885050acf4b3d31944431e1fd90d50664fb09126af4a3c050ba14ee8"),
    "PaddleOCR-VL-1.6-GGUF-mmproj.gguf": (881770560, "204d757d7610d9b3faab10d506d69e5b244e32bf765e2bab2d0167e65e0a058a"),
    "inference.pdiparams": (130806572, "70bd316b0582769ec968829fd1feb1a6a58b7c941b938327e551b6b12b45c137"),
}


def fetch(item):
    relative, url = item
    target = ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        temp = target.with_suffix(target.suffix + ".part")
        if target.name in LARGE:
            size, _ = LARGE[target.name]
            # Bounded range requests also work behind download-size-limited proxies.
            offset = temp.stat().st_size if temp.exists() else 0
            def ranged(start):
                end = min(size-1, start+1024*1024-1)
                for attempt in range(5):
                    try:
                        response = httpx.get(url+"?download=true", headers={"Range": f"bytes={start}-{end}"}, follow_redirects=True, timeout=30)
                        response.raise_for_status()
                        if response.status_code != 206 or response.headers.get("content-range") != f"bytes {start}-{end}/{size}" or len(response.content) != end-start+1:
                            raise ValueError("incorrect ranged model response")
                        return response.content
                    except Exception:
                        if attempt == 4:
                            raise
                        time.sleep(2)
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as chunks, temp.open("ab") as output:
                for chunk in chunks.map(ranged, range(offset, size, 1024*1024)):
                    output.write(chunk); output.flush()
                    offset += len(chunk)
                    if offset % (64*1024*1024) == 0:
                        print(f"Downloading {relative}: {offset//1048576} MiB", flush=True)
        else:
            with httpx.stream("GET", url, follow_redirects=True, timeout=120) as response, temp.open("wb") as output:
                response.raise_for_status()
                for chunk in response.iter_bytes(65536):
                    output.write(chunk)
        if target.name in LARGE:
            with temp.open("rb") as downloaded:
                if hashlib.file_digest(downloaded, "sha256").hexdigest() != LARGE[target.name][1]:
                    raise ValueError("model checksum mismatch")
        temp.replace(target)
    with target.open("rb") as downloaded:
        digest = hashlib.file_digest(downloaded, "sha256").hexdigest()
    if target.name in LARGE and digest != LARGE[target.name][1]:
        raise ValueError("existing model checksum mismatch")
    print(f"Ready: {relative} ({target.stat().st_size} bytes)", flush=True)
    return {"file": relative, "source": url, "bytes": target.stat().st_size, "sha256": digest}


if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        manifest = list(pool.map(fetch, ASSETS.items()))
    runtime = ROOT / "llama"
    runtime.mkdir(exist_ok=True)
    with zipfile.ZipFile(ROOT / "llama.zip") as archive:
        for member in archive.infolist():
            dest = (runtime / member.filename).resolve()
            if not dest.is_relative_to(runtime.resolve()):
                raise ValueError("unsafe archive path")
        archive.extractall(runtime)
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Provisioning complete. Start the local VLM from SANAD model controls.", flush=True)

"""Local, fixed-command CPU inference service owned by this API process."""
import json
import os
from pathlib import Path
import subprocess
import threading
import secrets
from urllib.request import urlopen
from .engines.base import EngineUnavailable


class VLMRuntime:
    def __init__(self, data_dir):
        self.root = Path(data_dir).resolve() / "models"
        self.process = None
        self.lock = threading.Lock()
        self.log = None
        self.key = os.getenv("SANAD_VLM_INTERNAL_KEY") or secrets.token_urlsafe(32)

    def executable(self):
        return next((self.root / "llama").rglob("llama-server.exe"), None)

    def status(self):
        weights = self.root / "paddle-vl"
        provisioned = (self.root / "manifest.json").is_file() and bool(self.executable()) and all(p.is_file() for p in [
            weights / "PaddleOCR-VL-1.6-GGUF.gguf", weights / "PaddleOCR-VL-1.6-GGUF-mmproj.gguf",
            self.root / "layout" / "inference.pdiparams"])
        healthy = False
        if self.process and self.process.poll() is None:
            try:
                with urlopen("http://127.0.0.1:8111/health", timeout=1) as response:
                    healthy = response.status == 200
            except Exception:
                pass
        state = "ready" if healthy else "starting" if self.process and self.process.poll() is None else "stopped" if provisioned else "not_provisioned"
        assets = {"paddle-vl/PaddleOCR-VL-1.6-GGUF.gguf": 935769056,
                  "paddle-vl/PaddleOCR-VL-1.6-GGUF-mmproj.gguf": 881770560,
                  "layout/inference.pdiparams": 130806572}
        present = 0
        for name, expected in assets.items():
            path = self.root / name
            path = path if path.exists() else path.with_suffix(path.suffix + ".part")
            present += min(expected, path.stat().st_size) if path.exists() else 0
        return {"state": state, "provisioned": provisioned, "assets_percent": round(100*present/sum(assets.values())),
                "device": "cpu", "model": "PaddleOCR-VL-1.6-0.9B",
                "backend": "llama.cpp b11717", "url": "http://127.0.0.1:8111/v1",
                "gemma_model": os.getenv("SANAD_GEMMA_MODEL", "gemma3:4b")}

    def start(self):
        with self.lock:
            status = self.status()
            if not status["provisioned"]:
                raise EngineUnavailable("VLM assets missing; run scripts/provision_vlm.py")
            if self.process and self.process.poll() is None:
                return status
            # Never adopt or terminate an unrelated process already on our port.
            import socket
            with socket.socket() as sock:
                if sock.connect_ex(("127.0.0.1", 8111)) == 0:
                    raise EngineUnavailable("port 8111 is already in use by another process")
            self.log = (self.root / "runtime.log").open("ab")
            weights = self.root / "paddle-vl"
            command = [str(self.executable()), "-m", str(weights / "PaddleOCR-VL-1.6-GGUF.gguf"),
                       "--mmproj", str(weights / "PaddleOCR-VL-1.6-GGUF-mmproj.gguf"),
                       "--host", "127.0.0.1", "--port", "8111", "--temp", "0", "-t", "4",
                       "-c", "8192", "--parallel", "1", "--n-gpu-layers", "0",
                       "--repeat-penalty", "1.1", "--repeat-last-n", "128",
                       "--alias", "PaddleOCR-VL-1.6-0.9B"]
            command.extend(["--api-key", self.key])
            self.process = subprocess.Popen(command, stdout=self.log, stderr=self.log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            return self.status()

    def stop(self):
        with self.lock:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=20)
            self.process = None
            if self.log:
                self.log.close()
                self.log = None
            return self.status()

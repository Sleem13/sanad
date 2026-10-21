"""Settings. Demo defaults are for SANAD_ENV=dev only; secure mode refuses demo auth."""
from __future__ import annotations
import os, json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    env: str = "dev"                     # dev | secure
    data_dir: Path = Path("./data")
    db_url: str = ""
    engine: str = "paddleocr_vl"     # paddleocr_arabic | paddleocr_vl
    allow_external_processing: bool = False   # must stay False unless institution authorizes
    dev_super_admin: bool = True              # local pilot session; never available in secure mode
    max_upload_bytes: int = 25 * 1024 * 1024
    max_image_pixels: int = 60_000_000   # decompression-bomb guard
    job_max_attempts: int = 3
    job_lease_seconds: int = 300
    backoff_base_seconds: int = 5
    users: dict = field(default_factory=dict)   # token -> {user, roles, orgs}

    @classmethod
    def from_env(cls) -> "Settings":
        s = cls()
        s.env = os.getenv("SANAD_ENV", "dev")
        s.data_dir = Path(os.getenv("SANAD_DATA_DIR", "./data"))
        s.db_url = os.getenv("SANAD_DB_URL", f"sqlite:///{s.data_dir}/sanad.db")
        s.engine = os.getenv("SANAD_ENGINE", "paddleocr_vl")
        if s.engine not in {"paddleocr_arabic", "paddleocr_vl", "paddleocr_vl_full_page"}:
            raise ValueError("SANAD_ENGINE must select a real pipeline: paddleocr_arabic, paddleocr_vl or paddleocr_vl_full_page")
        s.allow_external_processing = os.getenv("SANAD_ALLOW_EXTERNAL", "false").lower() == "true"
        uf = os.getenv("SANAD_USERS_FILE")
        s.dev_super_admin = s.env == "dev" and not uf
        if uf:
            s.users = json.loads(Path(uf).read_text())
        elif s.env == "dev":
            # DEMO ONLY tokens. Never used when SANAD_ENV=secure.
            s.users = {
                "demo-admin": {"user": "demo.admin", "roles": ["admin"], "orgs": ["*"]},
                "demo-operator": {"user": "demo.operator", "roles": ["operator"], "orgs": ["demo-court-a"]},
                "demo-reviewer1": {"user": "demo.reviewer1", "roles": ["reviewer"], "orgs": ["demo-court-a"]},
                "demo-reviewer2": {"user": "demo.reviewer2", "roles": ["reviewer"], "orgs": ["demo-court-a"]},
                "demo-supervisor": {"user": "demo.supervisor", "roles": ["supervisor", "reviewer"], "orgs": ["demo-court-a"]},
                "demo-operator-b": {"user": "demo.operator.b", "roles": ["operator"], "orgs": ["demo-court-b"]},
                "demo-other-org": {"user": "demo.other", "roles": ["reviewer"], "orgs": ["demo-court-b"]},
            }
        else:
            raise RuntimeError("SANAD_ENV=secure requires SANAD_USERS_FILE (no demo identities allowed)")
        return s

    def ensure_dirs(self) -> None:
        for sub in ("originals", "quarantine", "raw_outputs"):
            (self.data_dir / sub).mkdir(parents=True, exist_ok=True)

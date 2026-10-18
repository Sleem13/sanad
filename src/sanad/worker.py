"""Background worker: `python -m sanad.worker`. Polls the DB queue (pilot). Production: swap for a broker behind the same run_once()."""
import logging, time, os
from .config import Settings
from .db import make_session_factory
from .engines.paddleocr_vl import build_engine
from .pipeline import run_once

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg = Settings.from_env(); cfg.ensure_dirs()
    sf = make_session_factory(cfg.db_url)
    engine = build_engine(cfg.engine, cfg.allow_external_processing)
    logging.info("worker started engine=%s", cfg.engine)
    while True:
        out = run_once(sf, cfg, engine)
        if out is None:
            time.sleep(float(os.getenv("SANAD_POLL_SECONDS", "2")))

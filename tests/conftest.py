import io, sys, pathlib
import pytest
from fastapi.testclient import TestClient
from PIL import Image
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from sanad.config import Settings
from sanad.api import create_app
from fakes import StubEngine
from sanad import pipeline


def png_bytes(color="white", size=(400, 600), mark=0):
    im = Image.new("RGB", size, color)
    im.putpixel((mark % size[0], 0), (0, 0, 0))        # make distinct bytes per call
    b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()


@pytest.fixture
def env(tmp_path):
    cfg = Settings.from_env.__func__(Settings)          # dev defaults with demo users
    cfg.engine = "paddleocr_arabic"                               # the test worker is injected; no native OCR runs in unit tests
    cfg.data_dir = tmp_path
    cfg.db_url = f"sqlite:///{tmp_path}/t.db"
    cfg.backoff_base_seconds = 0
    app = create_app(cfg)
    return type("E", (), {"cfg": cfg, "app": app, "client": TestClient(app), "sf": app.state.sf})


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def upload(env, data, tok="demo-operator", org="demo-court-a", name="x.png"):
    return env.client.post("/api/v1/documents", headers=H(tok), data={"org_scope": org},
                           files={"file": (name, data, "application/octet-stream")})


def work(env, engine=None, n=1):
    engine = engine or StubEngine()
    return [pipeline.run_once(env.sf, env.cfg, engine) for _ in range(n)]


def first_page(env, doc_id, tok="demo-reviewer1"):
    return env.client.get(f"/api/v1/documents/{doc_id}", headers=H(tok)).json()["pages"][0]["id"]

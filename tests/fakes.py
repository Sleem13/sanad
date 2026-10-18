"""Test-only engine double. Never imported by the application."""
from __future__ import annotations
from sanad.engines.base import EngineResult, RawRegion

TEST_PREFIX = "[TEST-FIXTURE] "


class StubEngine:
    engine_id = "paddleocr_arabic"
    is_mock = False

    def __init__(self, fail_pages: set[int] | None = None, fail_times: int = 0, bad_linkage: bool = False):
        self.fail_pages, self.fail_times, self.bad_linkage = fail_pages or set(), fail_times, bad_linkage
        self._calls: dict[int, int] = {}

    def version(self) -> str:
        return "fixture-0"

    def config(self) -> dict:
        return {"warning": "TEST FIXTURE ONLY"}

    def recognize(self, image_path: str, width: int, height: int, page_no: int = 1) -> EngineResult:
        n = self._calls[page_no] = self._calls.get(page_no, 0) + 1
        if page_no in self.fail_pages and n <= self.fail_times:
            raise RuntimeError(f"simulated engine failure (page {page_no}, call {n})")
        bad = None if self.bad_linkage else [width * 0.1, height * 0.05, width * 0.9, height * 0.12]
        regions = [
            RawRegion("title", bad, TEST_PREFIX + "title placeholder", 0),
            RawRegion("text", [width * 0.1, height * 0.15, width * 0.9, height * 0.5], TEST_PREFIX + "body placeholder", 1),
            RawRegion("seal", [width * 0.6, height * 0.6, width * 0.85, height * 0.8], None, 2),
        ]
        return EngineResult(regions, {"fixture": True, "note": "synthetic placeholder output"})

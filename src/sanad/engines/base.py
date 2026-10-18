"""Version-neutral recognition-engine contract. Engines never call tools or URLs on behalf of document text."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, Optional


class EngineUnavailable(Exception):
    """Dependency/hardware/weights missing -> job becomes `blocked` (does not burn retry attempts)."""


@dataclass
class RawRegion:
    label: str
    bbox: list[float]
    text: Optional[str]
    reading_order: Optional[int] = None
    engine_score: Optional[float] = None
    engine_score_kind: Optional[str] = None
    polygon: Optional[list] = None
    extra: dict = field(default_factory=dict)


@dataclass
class EngineResult:
    regions: list[RawRegion]
    raw: dict                      # full raw engine output, persisted verbatim for provenance


class RecognitionEngine(Protocol):
    engine_id: str
    is_mock: bool
    def version(self) -> str: ...
    def config(self) -> dict: ...
    def recognize(self, image_path: str, width: int, height: int) -> EngineResult: ...

"""Provisional canonical representation (schema_version canonical-0.1). Owner Schema is applied later by an adapter."""
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = "canonical-0.1"
NON_TEXT_LABELS = {"image", "seal", "signature", "stamp", "figure", "chart"}


class RegionStatus(str, Enum):
    recognized = "recognized"
    uncertain = "uncertain"
    illegible = "illegible"
    not_present = "not_present"
    not_processed = "not_processed"
    requires_review = "requires_review"


class TableCell(BaseModel):
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    text: Optional[str] = None
    status: RegionStatus = RegionStatus.recognized


class Region(BaseModel):
    region_id: str
    label: str                                   # text, title, table, image, seal, signature, header, footer, margin_note ...
    bbox: list[float]                            # [x0,y0,x1,y1] in ORIGINAL page pixels, origin top-left
    polygon: Optional[list[list[float]]] = None
    text: Optional[str] = None                   # faithful transcription (never normalized)
    status: RegionStatus = RegionStatus.recognized
    reading_order: Optional[int] = None
    engine_score: Optional[float] = None         # raw engine score ONLY if the engine supplies one
    engine_score_kind: Optional[str] = None      # NOT calibrated accuracy
    flags: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    alternative_sources: list[str] = Field(default_factory=list)
    cells: Optional[list[TableCell]] = None

    @model_validator(mode="after")
    def _check(self):
        if len(self.bbox) != 4 or not (self.bbox[2] > self.bbox[0] and self.bbox[3] > self.bbox[1]):
            raise ValueError(f"region {self.region_id}: invalid bbox (source linkage required)")
        if (self.status == RegionStatus.recognized and self.cells is None
                and not (self.text or "").strip() and self.label not in NON_TEXT_LABELS):
            raise ValueError(f"region {self.region_id}: status=recognized requires text")
        if self.status in (RegionStatus.not_present, RegionStatus.not_processed) and self.text:
            raise ValueError(f"region {self.region_id}: {self.status.value} must not carry text")
        return self


class CanonicalPage(BaseModel):
    schema_version: str = SCHEMA_VERSION
    page_id: str
    page_no: int
    width: int
    height: int
    rotation: int = 0
    coordinate_system: str = "pixel_top_left_original"
    source_sha256: str
    regions: list[Region]

    @model_validator(mode="after")
    def _within_page(self):
        tol, ids = 2.0, set()
        for r in self.regions:
            if r.region_id in ids:
                raise ValueError(f"duplicate region_id {r.region_id}")
            ids.add(r.region_id)
            x0, y0, x1, y1 = r.bbox
            if x0 < -tol or y0 < -tol or x1 > self.width + tol or y1 > self.height + tol:
                raise ValueError(f"region {r.region_id}: bbox outside page")
        return self

    def text_in_reading_order(self) -> str:
        rs = [r for r in self.regions if r.text]
        rs.sort(key=lambda r: (r.reading_order is None, r.reading_order or 0))
        return "\n".join(r.text for r in rs)

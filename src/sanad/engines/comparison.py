"""Expose disagreements against an existing OCR run; never replace VLM text."""
import unicodedata


def attach_comparison(regions, baseline, source):
    def normal(text):
        return " ".join(unicodedata.normalize("NFC", text).split())
    for region in regions:
        if not region.text or region.label in {"image", "header_image", "footer_image"}:
            continue
        x,y,x1,y1 = region.bbox
        lines = []
        for old in baseline:
            if not old.get("text"):
                continue
            a,b,a1,b1 = old["bbox"]
            area = (a1-a)*(b1-b)
            overlap = max(0,min(a1,x1)-max(a,x))*max(0,min(b1,y1)-max(b,y))
            if area > 0 and overlap/area >= .6:
                lines.append(old)
        lines.sort(key=lambda r: r.get("reading_order") if r.get("reading_order") is not None else 10**9)
        text = "\n".join(r["text"] for r in lines)
        if text and normal(text) != normal(region.text):
            region.extra["alternatives"] = [text]
            region.extra["alternative_sources"] = [source]
            region.extra["flags"] = sorted(set(region.extra.get("flags",[])) | {"cross_engine_disagreement"})
            region.extra["requires_review"] = True

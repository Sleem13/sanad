"""Deterministic OCR preparation; never alters the archived source image."""
from PIL import Image

PROFILES = {"baseline", "upscale", "illumination", "contrast"}


def prepare(image, profile="upscale", target_side=1200, resize_backend="pillow"):
    if profile not in PROFILES:
        raise ValueError("unknown OCR preparation profile")
    original = image.convert("RGB")
    width, height = original.size
    factor = 1.0 if profile == "baseline" else max(1.0, min(4.0, target_side / max(width, height)))
    size = (round(width * factor), round(height * factor))
    working = original.resize(size, Image.Resampling.BICUBIC) if size != original.size else original.copy()
    if resize_backend == "opencv" and size != original.size:
        import cv2
        import numpy as np
        working = Image.fromarray(cv2.resize(np.asarray(original), size, interpolation=cv2.INTER_CUBIC))
    if profile in {"illumination", "contrast"}:
        import cv2
        import numpy as np
        pixels = np.asarray(working)
        if profile == "illumination":
            gray = cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY)
            background = cv2.GaussianBlur(gray, (0, 0), 25)
            gray = cv2.divide(gray, np.maximum(background, 1), scale=235)
            pixels = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        else:
            lab = cv2.cvtColor(pixels, cv2.COLOR_RGB2LAB)
            lab[:, :, 0] = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(lab[:, :, 0])
            pixels = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        working = Image.fromarray(pixels)
    return working, {"profile": profile, "source_size": [width, height], "working_size": list(working.size),
                     "scale_x": working.width / width, "scale_y": working.height / height,
                     "resize_backend": resize_backend}


def original_polygon(points, metadata):
    return [[float(x) / metadata["scale_x"], float(y) / metadata["scale_y"]] for x, y in points]


def merge_readings(primary, alternate):
    """Conservative, geometry-matched alternatives; disagreement always needs review.

    Raw engine scores guide candidate selection, never an accuracy estimate.
    Unmatched alternate detections are retained in raw output, not silently inserted.
    """
    import unicodedata

    def bounds(line):
        xs, ys = zip(*line["polygon"])
        return min(xs), min(ys), max(xs), max(ys)

    def similarity(a, b):
        ax, ay, ax1, ay1 = bounds(a)
        bx, by, bx1, by1 = bounds(b)
        if abs((ay+ay1)/2-(by+by1)/2) > min(ay1-ay, by1-by)*.5:
            return 0
        intersection = max(0, min(ax1, bx1)-max(ax, bx))*max(0, min(ay1, by1)-max(ay, by))
        union = (ax1-ax)*(ay1-ay)+(bx1-bx)*(by1-by)-intersection
        return intersection/union if union else 0

    def normalized(text):
        return " ".join(unicodedata.normalize("NFC", text).split())

    output, used = [], set()
    for line in primary:
        matches = [(similarity(line, other), i, other) for i, other in enumerate(alternate) if i not in used]
        overlap, index, candidate = max(matches, default=(0, -1, None), key=lambda m: m[0])
        chosen, alternatives = line, []
        if candidate is not None and overlap >= .45:
            used.add(index)
            if normalized(candidate["text"]) != normalized(line["text"]):
                alternatives = [dict(line), dict(candidate)]
                # Avoid selecting a shorter fragment merely because its score is higher.
                if (candidate["score"] > line["score"]+.08 and
                        len(candidate["text"].strip()) >= len(line["text"].strip())*.6):
                    chosen = candidate
        flags = []
        if alternatives:
            flags.append("ocr_disagreement")
        if chosen["score"] < .8:
            flags.append("low_ocr_score")
        if any(c.isdigit() for c in chosen["text"]):
            flags.append("numbers_need_review")
        output.append({**chosen, "alternatives": alternatives, "flags": flags,
                       "requires_review": bool(flags)})
    return output

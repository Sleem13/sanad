"""Real local engine factory. Native inference stays in the Paddle environment."""
from .local_vlm import LocalVLMEngine as PaddleOCRVLEngine


def build_engine(name: str, allow_external: bool = False, **kw):
    if name == "paddleocr_arabic":
        from .paddleocr_arabic import PaddleArabicEngine
        return PaddleArabicEngine(**kw)
    if name == "paddleocr_vl":
        return PaddleOCRVLEngine(**kw)
    raise ValueError(f"unknown engine {name}")

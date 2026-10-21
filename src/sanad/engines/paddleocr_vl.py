"""Real local engine factory. Native inference stays in the Paddle environment."""
from .local_vlm import LocalVLMEngine as PaddleOCRVLEngine


def build_engine(name: str, allow_external: bool = False, **kw):
    if name == "paddleocr_arabic":
        from .paddleocr_arabic import PaddleArabicEngine
        return PaddleArabicEngine(**kw)
    if name == "paddleocr_vl":
        return PaddleOCRVLEngine(**kw)
    if name == "paddleocr_vl_full_page":
        from .full_page_vlm import FullPageVLMEngine
        return FullPageVLMEngine(**kw)
    raise ValueError(f"unknown engine {name}")

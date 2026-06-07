"""W7 — OCR 기반 가시 라벨 탐지 엔진.

이미지 픽셀 내에 "AI 생성" 류 텍스트가 인쇄되어 있는지 OCR로 탐지한다.

엔진 우선순위: easyocr → pytesseract → UNKNOWN
  - easyocr: pip install easyocr (PyTorch 필요)
  - pytesseract: pip install pytesseract + 시스템 tesseract 설치 필요

판정 흐름:
  FOUND     : OCR 텍스트에서 AI 가시 라벨 패턴 발견
  NOT_FOUND : OCR 성공했으나 패턴 없음
  UNKNOWN   : OCR 엔진 미설치 또는 이미지 파싱 불가
"""
from __future__ import annotations

import io
import re
from typing import Optional

from PIL import Image, UnidentifiedImageError

from .base import DetectorBase
from .result import DetectionResult, DetectorOutput

# ---------------------------------------------------------------------------
# 가시 라벨 패턴 (한국어)
# ---------------------------------------------------------------------------
KO_LABEL_PATTERNS: list[str] = [
    r"AI\s*생성",
    r"AI\s*로\s*생성",
    r"AI\s*로\s*만들어진",
    r"인공지능\s*생성",
    r"인공지능\s*이\s*만든",
    r"AI\s*제작",
    r"AI\s*콘텐츠",
    r"생성\s*형\s*AI",
]

# ---------------------------------------------------------------------------
# 가시 라벨 패턴 (영문)
# ---------------------------------------------------------------------------
EN_LABEL_PATTERNS: list[str] = [
    r"AI[\s\-]?[Gg]enerated",
    r"[Mm]ade\s+with\s+AI",
    r"[Cc]reated\s+by\s+AI",
    r"[Cc]reated\s+with\s+AI",
    r"AI[\s\-]?[Cc]reated",
    r"[Gg]eneratedby\s*AI",
    r"AIGC",
    r"\[AI\]",
    r"#AI[Gg]enerated",
    r"AI[\s\-]produced",
]

# 오탐 방지 제외 패턴
_EXCLUSION_PATTERNS: list[str] = [
    r"^AI$",
    r"AI\s+art\s+style",
]

_COMBINED_PATTERN = re.compile(
    "|".join(f"(?:{p})" for p in KO_LABEL_PATTERNS + EN_LABEL_PATTERNS),
    re.IGNORECASE,
)
_EXCLUSION_RE = re.compile(
    "|".join(f"(?:{p})" for p in _EXCLUSION_PATTERNS),
    re.IGNORECASE,
)


def match_label_patterns(text: str) -> bool:
    """텍스트에서 AI 가시 라벨 패턴을 탐지한다."""
    if not text or not text.strip():
        return False
    if _EXCLUSION_RE.fullmatch(text.strip()):
        return False
    return bool(_COMBINED_PATTERN.search(text))


# ---------------------------------------------------------------------------
# OCR 엔진 탐지 (런타임 import)
# ---------------------------------------------------------------------------

def _ocr_with_easyocr(image_bytes: bytes) -> Optional[str]:
    """easyocr 로 이미지에서 텍스트를 추출한다."""
    try:
        import easyocr  # type: ignore[import]
        import numpy as np
        from PIL import Image as PILImage

        img = PILImage.open(io.BytesIO(image_bytes)).convert("RGB")
        arr = np.array(img)
        reader = easyocr.Reader(["ko", "en"], gpu=False, verbose=False)
        results = reader.readtext(arr, detail=0)
        return " ".join(results)
    except ImportError:
        return None
    except Exception:
        return None


def _ocr_with_pytesseract(image_bytes: bytes) -> Optional[str]:
    """pytesseract 로 이미지에서 텍스트를 추출한다."""
    try:
        import pytesseract  # type: ignore[import]
        from PIL import Image as PILImage

        img = PILImage.open(io.BytesIO(image_bytes)).convert("RGB")
        text = pytesseract.image_to_string(img, lang="kor+eng")
        return text
    except ImportError:
        return None
    except Exception:
        return None


def run_ocr(image_bytes: bytes) -> Optional[str]:
    """사용 가능한 OCR 엔진으로 텍스트를 추출한다. 모두 실패하면 None."""
    text = _ocr_with_easyocr(image_bytes)
    if text is not None:
        return text
    return _ocr_with_pytesseract(image_bytes)


def is_ocr_available() -> bool:
    """OCR 엔진이 하나라도 설치되어 있으면 True."""
    try:
        import easyocr  # noqa: F401
        return True
    except ImportError:
        pass
    try:
        import pytesseract  # noqa: F401
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# OCRDetector
# ---------------------------------------------------------------------------

class OCRDetector(DetectorBase):
    """픽셀 내 AI 가시 라벨 텍스트를 OCR로 탐지한다.

    easyocr 또는 pytesseract 중 하나가 설치되어 있어야 한다.
    없으면 항상 UNKNOWN 반환.
    """

    @property
    def name(self) -> str:
        return "ocr"

    def detect(self, image_bytes: bytes) -> DetectorOutput:
        # 이미지 유효성 확인
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()
        except (UnidentifiedImageError, Exception):
            return DetectorOutput(
                result=DetectionResult.UNKNOWN,
                detector_name=self.name,
                details={"reason": "image_not_readable"},
            )

        # OCR 실행
        ocr_text = run_ocr(image_bytes)
        if ocr_text is None:
            return DetectorOutput(
                result=DetectionResult.UNKNOWN,
                detector_name=self.name,
                details={"reason": "ocr_engine_not_available"},
            )

        # 패턴 매칭
        found = match_label_patterns(ocr_text)
        details: dict = {"ocr_text_preview": ocr_text[:300]}
        if found:
            return DetectorOutput(
                result=DetectionResult.FOUND,
                detector_name=self.name,
                details=details,
            )
        return DetectorOutput(
            result=DetectionResult.NOT_FOUND,
            detector_name=self.name,
            details=details,
        )

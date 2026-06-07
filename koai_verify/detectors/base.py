"""W5 — DetectorBase 추상 클래스.

W6+ 탐지 엔진이 구현해야 하는 인터페이스.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .result import DetectionResult, DetectorOutput


class DetectorBase(ABC):
    """AI 표시 탐지기 기반 클래스.

    각 탐지 엔진(C2PA, EXIF, OCR, Watermark)은 이 클래스를 상속한다.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """탐지기 이름 (리포트에 사용)."""

    @abstractmethod
    def detect(self, image_bytes: bytes) -> DetectorOutput:
        """이미지 bytes 에서 AI 표시를 탐지한다.

        탐지 불가 케이스는 반드시 DetectionResult.UNKNOWN 반환.
        절대 추정 금지.
        """

    def detect_safe(self, image_bytes: bytes) -> DetectorOutput:
        """예외 안전 래퍼 — 내부 오류를 UNKNOWN 으로 흡수한다."""
        try:
            return self.detect(image_bytes)
        except Exception as e:
            return DetectorOutput(
                result=DetectionResult.UNKNOWN,
                detector_name=self.name,
                details={"error": str(e)},
            )

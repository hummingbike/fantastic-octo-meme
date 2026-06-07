"""W5 — 탐지 결과 타입 정의.

W6+ 탐지 엔진이 공통으로 사용하는 결과 타입.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DetectionResult(str, Enum):
    """탐지 결과 열거형.

    FOUND: 표시가 탐지됨.
    NOT_FOUND: 탐지 시도했으나 없음.
    UNKNOWN: 탐지 자체 불가 (비공개 API, 키 없음 등).
    """

    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    UNKNOWN = "UNKNOWN"  # 과대주장 금지 — 없다고 단정하지 않음


@dataclass
class DetectorOutput:
    """단일 탐지기 실행 결과."""

    result: DetectionResult
    detector_name: str
    details: dict[str, Any] = field(default_factory=dict)
    confidence: float | None = None  # 0.0–1.0, 미측정이면 None

    def is_found(self) -> bool:
        return self.result == DetectionResult.FOUND

    def is_unknown(self) -> bool:
        return self.result == DetectionResult.UNKNOWN

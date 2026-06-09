"""W3 강건성 벤치마크 — 측정 매트릭스 설계.

매트릭스 구조:
  행(Row)    : 탐지 포맷 (C2PA / EXIF / 가시라벨 / 오픈워터마크)
  열(Column) : 변형 타입 (TRANSFORM_BATTERY 의 각 TransformSpec)
  값         : 탐지 생존율 0.0–1.0 (None = 미측정)

이 모듈은 W3 설계 산출물이며, 실제 측정은 W9 강건성 하니스에서 수행한다.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional

from benchmarks.transform_spec import TRANSFORM_BATTERY, TransformSpec


class DetectionFormat(str, Enum):
    """탐지 대상 포맷 분류 (R-01~R-04 룰과 대응)."""

    C2PA = "c2pa"  # R-01: C2PA 매니페스트
    EXIF = "exif"  # R-02: EXIF/XMP AI 플래그
    VISIBLE_LABEL = "visible_label"  # R-04: 가시 라벨 (OCR)
    OPEN_WATERMARK = "open_watermark"  # 오픈 워터마크 (키 있을 때)


@dataclass
class SurvivalCell:
    """매트릭스 한 셀 — 포맷 × 변형 조합의 탐지 생존율."""

    format: DetectionFormat
    transform_label: str
    survival_rate: Optional[float] = None  # None = 미측정, 0.0–1.0

    def is_measured(self) -> bool:
        return self.survival_rate is not None

    def passes_threshold(self, threshold: float = 0.8) -> bool:
        """생존율이 임계치 이상이면 True (R-06 경고 판단 기준)."""
        if self.survival_rate is None:
            return False
        return self.survival_rate >= threshold


@dataclass
class SurvivalMatrix:
    """포맷 × 변형 전체 매트릭스."""

    cells: list[SurvivalCell] = field(default_factory=list)

    def get(self, fmt: DetectionFormat, transform_label: str) -> Optional[SurvivalCell]:
        for cell in self.cells:
            if cell.format == fmt and cell.transform_label == transform_label:
                return cell
        return None

    def set_rate(self, fmt: DetectionFormat, transform_label: str, rate: float) -> None:
        cell = self.get(fmt, transform_label)
        if cell is not None:
            cell.survival_rate = rate
        else:
            self.cells.append(SurvivalCell(fmt, transform_label, rate))

    def measured_cells(self) -> list[SurvivalCell]:
        return [c for c in self.cells if c.is_measured()]

    def failing_cells(self, threshold: float = 0.8) -> list[SurvivalCell]:
        """임계치 미달 셀 목록 (R-06 경고 트리거 후보)."""
        return [c for c in self.cells if c.is_measured() and not c.passes_threshold(threshold)]

    def to_dict(self) -> dict:
        return {"cells": [asdict(c) for c in self.cells]}

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "SurvivalMatrix":
        cells = [
            SurvivalCell(
                format=DetectionFormat(c["format"]),
                transform_label=c["transform_label"],
                survival_rate=c["survival_rate"],
            )
            for c in data["cells"]
        ]
        return cls(cells=cells)


def empty_matrix(
    formats: list[DetectionFormat] | None = None,
    battery: list[TransformSpec] | None = None,
) -> SurvivalMatrix:
    """모든 셀을 미측정(None) 으로 초기화한 빈 매트릭스를 생성한다."""
    if formats is None:
        formats = list(DetectionFormat)
    if battery is None:
        battery = TRANSFORM_BATTERY
    cells = [SurvivalCell(fmt, spec.label(), None) for fmt in formats for spec in battery]
    return SurvivalMatrix(cells=cells)


# ---------------------------------------------------------------------------
# 매트릭스 집계 유틸리티
# ---------------------------------------------------------------------------


def format_survival_summary(matrix: SurvivalMatrix) -> dict[str, dict[str, float | None]]:
    """포맷별 변형별 생존율을 중첩 딕셔너리로 반환한다."""
    summary: dict[str, dict[str, float | None]] = {}
    for cell in matrix.cells:
        fmt_key = cell.format.value
        if fmt_key not in summary:
            summary[fmt_key] = {}
        summary[fmt_key][cell.transform_label] = cell.survival_rate
    return summary


def worst_transforms(
    matrix: SurvivalMatrix,
    fmt: DetectionFormat,
    top_n: int = 5,
) -> list[SurvivalCell]:
    """특정 포맷에서 생존율이 가장 낮은 변형 top_n 개를 반환한다."""
    cells = [c for c in matrix.cells if c.format == fmt and c.is_measured()]
    return sorted(cells, key=lambda c: c.survival_rate or 0.0)[:top_n]


# ---------------------------------------------------------------------------
# R-06 룰 연계: 강건성 임계치
# ---------------------------------------------------------------------------

# PRD §4 R-06: 생존율 < 임계치 → WARNING
ROBUSTNESS_THRESHOLD = 0.8  # 80%


def evaluate_robustness(matrix: SurvivalMatrix, threshold: float = ROBUSTNESS_THRESHOLD) -> dict:
    """매트릭스에서 R-06 경고 판정을 수행한다."""
    failing = matrix.failing_cells(threshold)
    return {
        "threshold": threshold,
        "total_measured": len(matrix.measured_cells()),
        "failing_count": len(failing),
        "r06_triggered": len(failing) > 0,
        "failing_cells": [
            {"format": c.format.value, "transform": c.transform_label, "rate": c.survival_rate} for c in failing
        ],
    }

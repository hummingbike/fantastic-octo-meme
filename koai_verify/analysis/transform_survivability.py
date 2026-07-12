"""W4 — 변형 후 마킹 생존 케이스 식별.

각 도구의 합성 픽스처에 W3 변형 배터리를 적용해
"어떤 변형에서 어떤 마킹이 깨지는가"를 분석한다.

실제 대규모 측정은 W9 강건성 하니스에서 수행.
여기서는 케이스 식별(break/survive 분류) 프레임워크를 구축한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from koai_verify.analysis.tool_fingerprint import (
    MarkingPresence,
    ToolFingerprint,
    fingerprint_image,
)
from koai_verify.robustness.transform_spec import TRANSFORM_BATTERY, TransformSpec, apply_transform


class SurvivalOutcome(str, Enum):
    SURVIVED = "survived"  # 변형 후에도 마킹 탐지됨
    BROKEN = "broken"  # 변형 후 마킹 소실
    UNKNOWN = "unknown"  # 원본도 탐지 불가 → 비교 불가


@dataclass
class TransformSurvivalResult:
    """단일 변형·단일 마킹 타입의 생존 결과."""

    transform_label: str
    marking_type: str  # "exif_ai" | "c2pa" | "visible_label"
    before: MarkingPresence
    after: MarkingPresence
    outcome: SurvivalOutcome


@dataclass
class ToolTransformReport:
    """도구 하나의 변형 배터리 전체 생존 결과."""

    tool_name: str
    original_fingerprint: ToolFingerprint
    results: list[TransformSurvivalResult]

    def broken_cases(self) -> list[TransformSurvivalResult]:
        return [r for r in self.results if r.outcome == SurvivalOutcome.BROKEN]

    def survived_cases(self) -> list[TransformSurvivalResult]:
        return [r for r in self.results if r.outcome == SurvivalOutcome.SURVIVED]

    def survival_rate(self, marking_type: str) -> Optional[float]:
        """지정 마킹 타입의 생존율 (0.0–1.0). 측정 불가면 None."""
        relevant = [r for r in self.results if r.marking_type == marking_type]
        measurable = [r for r in relevant if r.outcome != SurvivalOutcome.UNKNOWN]
        if not measurable:
            return None
        survived = sum(1 for r in measurable if r.outcome == SurvivalOutcome.SURVIVED)
        return survived / len(measurable)


def _compare_presence(before: MarkingPresence, after: MarkingPresence) -> SurvivalOutcome:
    if before == MarkingPresence.UNKNOWN:
        return SurvivalOutcome.UNKNOWN
    if before == MarkingPresence.NOT_FOUND:
        return SurvivalOutcome.UNKNOWN  # 원본에서 없었으면 비교 불가
    # before == FOUND
    if after == MarkingPresence.FOUND:
        return SurvivalOutcome.SURVIVED
    return SurvivalOutcome.BROKEN


def analyze_transform_survival(
    image_bytes: bytes,
    tool_name: str,
    battery: list[TransformSpec] | None = None,
) -> ToolTransformReport:
    """이미지에 변형 배터리를 적용하고 마킹 생존 케이스를 분석한다."""
    if battery is None:
        battery = TRANSFORM_BATTERY

    original_fp = fingerprint_image(image_bytes, tool_name)
    results: list[TransformSurvivalResult] = []

    for spec in battery:
        transformed = apply_transform(image_bytes, spec)
        transformed_fp = fingerprint_image(transformed, tool_name)

        for marking_type in ("exif_ai", "c2pa"):
            before = getattr(original_fp, marking_type)
            after = getattr(transformed_fp, marking_type)
            outcome = _compare_presence(before, after)
            results.append(
                TransformSurvivalResult(
                    transform_label=spec.label(),
                    marking_type=marking_type,
                    before=before,
                    after=after,
                    outcome=outcome,
                )
            )

    return ToolTransformReport(
        tool_name=tool_name,
        original_fingerprint=original_fp,
        results=results,
    )


# ---------------------------------------------------------------------------
# 알려진 케이스 분류 (공개 문서 기반 — W9 실측 전 사전 정의)
# ---------------------------------------------------------------------------

KNOWN_BREAK_CASES: list[dict] = [
    # C2PA
    {
        "tool": "adobe_firefly",
        "marking": "c2pa",
        "breaking_transforms": [
            "sns_instagram",
            "sns_twitter",
            "sns_kakaotalk_chat",
            "sns_kakaotalk_profile",
            "screenshot_96dpi",
            "screenshot_72dpi",
            "jpeg_compress_q80",  # 재압축 시 JUMBF 박스 유실
            "webp_convert_q90",  # 컨테이너 변경
        ],
        "surviving_transforms": [],  # 실질적으로 없음
        "survival_rate_estimate": 0.0,
        "reason": "C2PA는 JUMBF 바이너리 박스 — 재압축·컨테이너 변경 시 전부 유실",
    },
    # EXIF AI
    {
        "tool": "stable_diffusion",
        "marking": "exif_ai",
        "breaking_transforms": [
            "sns_instagram",
            "sns_twitter",
            "sns_kakaotalk_chat",
            "sns_kakaotalk_profile",
            "screenshot_96dpi",
            "screenshot_72dpi",
        ],
        "surviving_transforms": [
            "jpeg_compress_q80",
            "jpeg_compress_q60",
            "resize_75pct",
            "resize_50pct",
            "crop_center_90pct",
        ],
        "survival_rate_estimate": 0.5,  # SNS에서 모두 유실, 직접 조작에서는 생존
        "reason": "EXIF는 SNS 플랫폼이 제거, 스크린샷 시 소거. 단순 압축·리사이즈에서는 생존 가능.",
    },
    # 가시 라벨 (OCR 탐지 대상)
    {
        "tool": "generic_visible_label",
        "marking": "visible_label",
        "breaking_transforms": [
            "resize_25pct",  # 극단적 축소 시 OCR 불가
            "jpeg_compress_q20",  # 심한 압축으로 텍스트 뭉개짐
            "crop_center_70pct",  # 라벨이 외곽에 있으면 잘림
        ],
        "surviving_transforms": [
            "jpeg_compress_q80",
            "jpeg_compress_q60",
            "resize_75pct",
            "resize_50pct",
            "sns_instagram",
            "sns_twitter",  # 이미지 자체에 텍스트가 있으면 생존
        ],
        "survival_rate_estimate": 0.75,
        "reason": "픽셀 데이터에 포함된 가시 라벨은 이미지 재인코딩에 강건. 극단적 변형에서만 손상.",
    },
]

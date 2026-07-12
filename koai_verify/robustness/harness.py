"""W9 — 강건성 하니스.

변형 배터리를 실행하고 탐지기별 생존율을 측정한다.

흐름:
  원본 이미지
    → 변형 배터리 적용 (압축/리사이즈/크롭/재인코딩)
    → 각 변형본에 탐지기 실행
    → 탐지 생존율 집계
    → SurvivalReport 반환

run_battery() 결과의 to_robustness_dict() 는 RuleEngine.evaluate() 의
robustness 인자로 직접 사용할 수 있다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from koai_verify.detectors.base import DetectorBase
from koai_verify.detectors.result import DetectionResult
from koai_verify.robustness.transform_spec import TRANSFORM_BATTERY, TransformSpec, apply_transform


def transform(image_bytes: bytes, spec: TransformSpec) -> bytes:
    """단일 변형 적용 — apply_transform 의 공개 래퍼."""
    return apply_transform(image_bytes, spec)


@dataclass
class TransformEntry:
    """단일 변형에 대한 탐지 결과."""

    transform_label: str
    result: DetectionResult
    survived: bool | None
    """True=생존, False=소실, None=원본 탐지 불가(비교 의미 없음)."""


@dataclass
class SurvivalReport:
    """강건성 하니스 실행 결과."""

    detector_name: str
    original_result: DetectionResult
    entries: list[TransformEntry] = field(default_factory=list)

    def survival_rate(self) -> float | None:
        """측정 가능한 변형 중 생존 비율 (0.0–1.0).

        원본 탐지 불가(UNKNOWN/NOT_FOUND)이면 None.
        """
        measurable = [e for e in self.entries if e.survived is not None]
        if not measurable:
            return None
        return sum(1 for e in measurable if e.survived) / len(measurable)

    def surviving(self) -> list[TransformEntry]:
        """생존한 변형 목록."""
        return [e for e in self.entries if e.survived is True]

    def broken(self) -> list[TransformEntry]:
        """소실된 변형 목록."""
        return [e for e in self.entries if e.survived is False]

    def to_robustness_dict(self) -> dict[str, float]:
        """RuleEngine.evaluate() robustness 인자용 dict.

        detector_name → 생존율 (0.0–1.0).
        원본 탐지 불가면 빈 dict 반환.
        """
        rate = self.survival_rate()
        if rate is None:
            return {}
        return {self.detector_name: rate}


def run_battery(
    image_bytes: bytes,
    detector: DetectorBase,
    battery: list[TransformSpec] | None = None,
) -> SurvivalReport:
    """이미지에 변형 배터리를 적용하고 탐지기 생존율을 측정한다.

    Args:
        image_bytes: 원본 이미지 bytes.
        detector: 실행할 탐지기 (DetectorBase 구현체).
        battery: 적용할 변형 목록. None 이면 TRANSFORM_BATTERY 전체 사용.

    Returns:
        SurvivalReport — 변형별 탐지 결과 및 생존율.
    """
    if battery is None:
        battery = TRANSFORM_BATTERY

    original_output = detector.detect_safe(image_bytes)
    original_result = original_output.result

    entries: list[TransformEntry] = []
    for spec in battery:
        transformed = apply_transform(image_bytes, spec)
        output = detector.detect_safe(transformed)

        if original_result == DetectionResult.FOUND:
            survived: bool | None = output.result == DetectionResult.FOUND
        else:
            survived = None  # 원본 탐지 불가 → 비교 불가

        entries.append(
            TransformEntry(
                transform_label=spec.label(),
                result=output.result,
                survived=survived,
            )
        )

    return SurvivalReport(
        detector_name=detector.name,
        original_result=original_result,
        entries=entries,
    )

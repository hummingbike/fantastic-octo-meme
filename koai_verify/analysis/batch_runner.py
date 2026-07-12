"""W14 — Phase 0 배치 분석기.

tests/fixtures/samples/ 아래 도구별 이미지를 실제 검증기로 실행해
갭 리포트 v1을 위한 집계 데이터를 생성한다.

설계:
  - verify() API 로 각 샘플을 검증
  - 도구별 결과를 ToolVerifyResult 로 집계
  - KNOWN_TOOL_CATALOG 예측과 실제 결과를 대조
  - SNS 변형 배터리로 생존율 실측
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PLACEHOLDER_SUFFIX = "_placeholder"

# SNS 시뮬 변형 레이블 (koai_verify/robustness/transform_spec.py TransformType)
SNS_TRANSFORM_LABELS = [
    "sns_instagram",
    "sns_twitter",
    "sns_kakaotalk_chat",
    "sns_kakaotalk_profile",
]


# ---------------------------------------------------------------------------
# 결과 데이터 모델
# ---------------------------------------------------------------------------


@dataclass
class ToolVerifyResult:
    """도구 하나의 배치 검증 결과 집계."""

    tool_name: str
    sample_count: int
    is_placeholder: bool
    verdicts: list[str]  # per-sample verdict 문자열
    triggered_rules: list[list[str]]  # per-sample
    detections: list[dict]  # per-sample: {"c2pa": "FOUND", ...}
    sns_survival: dict[str, float]  # sns_label → survival_rate (0.0–1.0), -1.0 이면 원본에 마킹 없어 측정 불가

    def dominant_verdict(self) -> str:
        """샘플 중 가장 많이 나온 verdict."""
        if not self.verdicts:
            return "UNKNOWN"
        from collections import Counter

        return Counter(self.verdicts).most_common(1)[0][0]

    def gap_category(self) -> str:
        """검증 결과로부터 도구의 갭 분류를 도출한다.

        Returns:
            "NO_MARKING" | "INVISIBLE_ONLY" | "DETECTABLE" | "UNKNOWN"
        """
        if self.is_placeholder:
            return "UNKNOWN"

        dominant = self.dominant_verdict()

        # 판정이 NON_COMPLIANT 이고 R-05 트리거인 경우 → 마킹 전혀 없음
        for rules in self.triggered_rules:
            if "R-05" in (rules or []):
                pass
        failing_rules_flat = []
        for rules in self.triggered_rules:
            failing_rules_flat.extend(rules or [])

        if dominant == "NON_COMPLIANT":
            if "R-05" in failing_rules_flat:
                return "NO_MARKING"
            if "R-03B" in failing_rules_flat:
                return "INVISIBLE_ONLY"
            return "NO_MARKING"
        if dominant == "WARNING":
            return "INVISIBLE_ONLY"
        if dominant == "COMPLIANT":
            return "DETECTABLE"
        return "UNKNOWN"

    def sns_mean_survival(self) -> float:
        """SNS 변형 평균 생존율. 측정 불가(-1.0)를 제외한 평균."""
        measurable = [v for v in self.sns_survival.values() if v >= 0.0]
        if not measurable:
            return -1.0
        return sum(measurable) / len(measurable)


@dataclass
class BatchAnalysisReport:
    """Phase 0 전체 샘플 배치 분석 리포트."""

    analyzed_at: str
    total_samples: int
    tool_results: dict[str, ToolVerifyResult] = field(default_factory=dict)

    def gap_summary(self) -> dict[str, str]:
        """도구명 → 갭 분류 요약."""
        return {name: r.gap_category() for name, r in self.tool_results.items()}

    def tools_by_gap(self) -> dict[str, list[str]]:
        """갭 분류 → 도구 목록 역인덱스."""
        from collections import defaultdict

        result: dict[str, list[str]] = defaultdict(list)
        for name, category in self.gap_summary().items():
            result[category].append(name)
        return dict(result)

    def comparison_with_catalog(self) -> dict[str, dict]:
        """KNOWN_TOOL_CATALOG 예측 vs 실제 결과 대조."""
        from koai_verify.analysis.tool_fingerprint import KNOWN_TOOL_CATALOG

        comparison: dict[str, dict] = {}
        for tool_name, result in self.tool_results.items():
            catalog_entry = KNOWN_TOOL_CATALOG.get(tool_name, {})
            predicted = catalog_entry.get("known_gap", "unknown")
            predicted_str = predicted.value if hasattr(predicted, "value") else str(predicted)
            actual = result.gap_category()
            comparison[tool_name] = {
                "predicted_gap": predicted_str,
                "actual_gap": actual,
                "verdict": result.dominant_verdict(),
                "is_placeholder": result.is_placeholder,
                "match": predicted_str.lower() == actual.lower(),
            }
        return comparison

    def overall_noncompliant_rate(self) -> float:
        """전체 샘플 중 NON_COMPLIANT 비율."""
        if self.total_samples == 0:
            return 0.0
        noncompliant = sum(v == "NON_COMPLIANT" for r in self.tool_results.values() for v in r.verdicts)
        return noncompliant / self.total_samples


# ---------------------------------------------------------------------------
# 배치 분석 실행
# ---------------------------------------------------------------------------


def run_batch_analysis(
    samples_dir: Path,
    *,
    sns_robustness: bool = False,
) -> BatchAnalysisReport:
    """samples_dir 아래 도구별 이미지를 검증기로 실행해 집계한다.

    Args:
        samples_dir: tests/fixtures/samples/ 디렉터리.
        sns_robustness: True 이면 SNS 변형 배터리로 생존율을 측정한다.

    Returns:
        BatchAnalysisReport
    """
    from koai_verify.api import verify

    analyzed_at = datetime.now(timezone.utc).isoformat()
    tool_results: dict[str, ToolVerifyResult] = {}
    total_samples = 0

    for tool_dir in sorted(samples_dir.iterdir()):
        if not tool_dir.is_dir():
            continue
        tool_name = tool_dir.name
        jpg_files = sorted(tool_dir.glob("*.jpg"))
        if not jpg_files:
            continue

        is_placeholder = all(PLACEHOLDER_SUFFIX in p.stem for p in jpg_files)

        verdicts: list[str] = []
        all_triggered: list[list[str]] = []
        all_detections: list[dict] = []

        for img_path in jpg_files:
            try:
                report = verify(img_path)
            except Exception:
                verdicts.append("UNKNOWN")
                all_triggered.append([])
                all_detections.append({})
                continue

            verdicts.append(report.verdict.value if hasattr(report.verdict, "value") else str(report.verdict))
            all_triggered.append(list(report.triggered_rules or []))
            all_detections.append(dict(report.detections or {}))
            total_samples += 1

        # SNS 생존율 측정
        sns_survival: dict[str, float] = {}
        if sns_robustness and jpg_files and not is_placeholder:
            sns_survival = _measure_sns_survival(jpg_files[0])
        elif sns_robustness:
            sns_survival = {label: -1.0 for label in SNS_TRANSFORM_LABELS}

        tool_results[tool_name] = ToolVerifyResult(
            tool_name=tool_name,
            sample_count=len(jpg_files),
            is_placeholder=is_placeholder,
            verdicts=verdicts,
            triggered_rules=all_triggered,
            detections=all_detections,
            sns_survival=sns_survival,
        )

    return BatchAnalysisReport(
        analyzed_at=analyzed_at,
        total_samples=total_samples,
        tool_results=tool_results,
    )


def _measure_sns_survival(image_path: Path) -> dict[str, float]:
    """단일 이미지에 SNS 변형을 적용해 마킹 생존율을 측정한다.

    원본에서 EXIF 또는 C2PA 가 탐지되지 않으면 -1.0(측정 불가)을 반환한다.

    Returns:
        {sns_label: survival_rate (0.0 or 1.0, -1.0 if not measurable)}
    """
    from koai_verify.detectors.c2pa_detector import C2PADetector
    from koai_verify.detectors.exif_detector import EXIFDetector
    from koai_verify.detectors.result import DetectionResult
    from koai_verify.robustness.transform_spec import TRANSFORM_BATTERY, apply_transform

    image_bytes = image_path.read_bytes()
    exif_det = EXIFDetector()
    c2pa_det = C2PADetector()

    # 원본 탐지
    orig_exif = exif_det.detect_safe(image_bytes).result
    orig_c2pa = c2pa_det.detect_safe(image_bytes).result

    has_original_marking = orig_exif == DetectionResult.FOUND or orig_c2pa == DetectionResult.FOUND

    # SNS 변형 배터리 필터링
    sns_specs = [s for s in TRANSFORM_BATTERY if s.label() in SNS_TRANSFORM_LABELS]

    result: dict[str, float] = {}
    for spec in sns_specs:
        label = spec.label()
        if not has_original_marking:
            result[label] = -1.0
            continue
        try:
            transformed = apply_transform(image_bytes, spec)
            after_exif = exif_det.detect_safe(transformed).result
            after_c2pa = c2pa_det.detect_safe(transformed).result
            survived = after_exif == DetectionResult.FOUND or after_c2pa == DetectionResult.FOUND
            result[label] = 1.0 if survived else 0.0
        except Exception:
            result[label] = -1.0

    # 정의된 레이블 중 배터리에 없는 것은 -1.0
    for label in SNS_TRANSFORM_LABELS:
        if label not in result:
            result[label] = -1.0

    return result


# ---------------------------------------------------------------------------
# 픽스처 경로 해석 헬퍼
# ---------------------------------------------------------------------------


def get_tool_name_from_dir(tool_dir: Path) -> Optional[str]:
    """디렉터리 이름으로 도구명을 반환한다."""
    return tool_dir.name if tool_dir.is_dir() else None

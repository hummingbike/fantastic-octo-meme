"""한국법 룰 엔진 (R-01~R-07).

입력: 탐지기 결과 dict 또는 DetectorOutput 리스트 + 검증 컨텍스트
출력: RuleVerdict (판정 + 트리거 규칙 + 권고문)

룰 평가 우선순위:
  R-05 → R-04 → R-01/R-02 → R-03 → R-07 → R-06
"""
from __future__ import annotations

from koai_verify.detectors.result import DetectorOutput

from .models import RuleVerdict, Verdict, VerificationContext

_ROBUSTNESS_THRESHOLD = 0.70

DetectionsDict = dict[str, str]
"""탐지 결과 dict: {"c2pa": "FOUND", "exif": "NOT_FOUND", "ocr": "FOUND", "watermark": "UNKNOWN"}"""


def _priority(result_str: str) -> int:
    return {"FOUND": 2, "UNKNOWN": 1, "NOT_FOUND": 0}.get(result_str, 0)


def aggregate_detections(outputs: list[DetectorOutput]) -> DetectionsDict:
    """DetectorOutput 리스트를 DetectionsDict 로 변환한다.

    같은 detector_name 이 여러 번 나올 경우 FOUND > UNKNOWN > NOT_FOUND 우선순위 적용.
    """
    result: DetectionsDict = {}
    for output in outputs:
        name = output.detector_name
        value = output.result.value
        existing = result.get(name)
        if existing is None or _priority(value) > _priority(existing):
            result[name] = value
    return result


class RuleEngine:
    """한국 AI 기본법 제31조 룰 엔진."""

    robustness_threshold: float

    def __init__(self, robustness_threshold: float = _ROBUSTNESS_THRESHOLD) -> None:
        self.robustness_threshold = robustness_threshold

    def evaluate_outputs(
        self,
        outputs: list[DetectorOutput],
        context: VerificationContext | None = None,
        robustness: dict[str, float] | None = None,
    ) -> RuleVerdict:
        """DetectorOutput 리스트를 집계해 룰을 평가한다.

        4개 탐지기(C2PA/EXIF/OCR/Watermark) 출력을 받아
        R-01~R-07 룰 평가 → RuleVerdict 를 반환한다.
        """
        return self.evaluate(aggregate_detections(outputs), context, robustness)

    def evaluate(
        self,
        detections: DetectionsDict,
        context: VerificationContext | None = None,
        robustness: dict[str, float] | None = None,
    ) -> RuleVerdict:
        """탐지 결과로 판정을 수행한다.

        Args:
            detections: 탐지기별 결과. 키: "c2pa"/"exif"/"ocr"/"watermark", 값: "FOUND"/"NOT_FOUND"/"UNKNOWN"
            context: 서비스 배포 컨텍스트. None 이면 모두 불명으로 처리.
            robustness: 탐지기별 생존율(0.0~1.0). R-06 평가에 사용.
        """
        ctx = context or VerificationContext()
        triggered: list[str] = []
        failing: list[str] = []

        c2pa = detections.get("c2pa", "UNKNOWN")
        exif = detections.get("exif", "UNKNOWN")
        ocr = detections.get("ocr", "NOT_FOUND")
        watermark = detections.get("watermark", "UNKNOWN")

        visible_found = (ocr == "FOUND")
        c2pa_found = (c2pa == "FOUND")
        exif_found = (exif == "FOUND")
        invisible_found = c2pa_found or exif_found
        watermark_found = (watermark == "FOUND")

        # R-05: 어떤 표시도 없음 → 즉시 NON_COMPLIANT
        if not visible_found and not invisible_found and not watermark_found:
            failing.append("R-05")
            return RuleVerdict(
                verdict=Verdict.NON_COMPLIANT,
                triggered_rules=triggered,
                failing_rules=failing,
                recommendation=(
                    "AI 생성 표시를 찾을 수 없습니다. 아래 방법 중 하나 이상을 적용하세요:\n"
                    "① C2PA 매니페스트 삽입  "
                    "② EXIF/XMP AI 메타데이터  "
                    "③ 가시 라벨 (이미지 내 'AI 생성' 등)\n"
                    "기계 판독 방식 사용 시 다운로드/배포 시 1회 이상 안내 필수 (시행령 제23조 제2항)."
                ),
            )

        verdict: Verdict
        recommendation: str

        # R-04: 가시 라벨 → 사람 인식 방법 충족
        if visible_found:
            triggered.append("R-04")
            verdict = Verdict.COMPLIANT
            recommendation = "가시 라벨이 탐지됐습니다. 사람이 인식할 수 있는 표시 방법을 갖추고 있습니다."

        # R-01/R-02: 비가시 마킹만 있는 경우 → R-03 컨텍스트 판정
        elif invisible_found:
            if c2pa_found:
                triggered.append("R-01")
            if exif_found:
                triggered.append("R-02")

            # R-03 케이스 A: 1회 안내 확인됨
            if ctx.download_notice_confirmed is True:
                triggered.append("R-03A")
                verdict = Verdict.COMPLIANT
                recommendation = (
                    "비가시 표시와 배포 시 1회 안내가 확인됐습니다. 시행령 제23조 제2항 요건을 충족합니다."
                )

            # R-03 케이스 B: 안내 없이 외부 배포 → NON_COMPLIANT
            elif ctx.download_notice_confirmed is False and ctx.is_external_distribution is True:
                failing.append("R-03B")
                verdict = Verdict.NON_COMPLIANT
                recommendation = (
                    "비가시 표시(메타데이터)만 탐지됐으나 외부 배포 시 필수인 1회 안내 문구가 없습니다.\n"
                    "다운로드 시 'AI로 생성된 이미지입니다' 등의 안내를 1회 이상 제공하거나\n"
                    "이미지 내 가시 라벨을 추가하세요 (시행령 제23조 제2항)."
                )

            # R-03 케이스 C: 컨텍스트 불명 → WARNING
            else:
                triggered.append("R-03C")
                verdict = Verdict.WARNING
                recommendation = (
                    "비가시 표시(메타데이터)만 탐지됐습니다. "
                    "이미지를 외부로 배포하는 경우 배포 시 AI 생성 사실을\n"
                    "1회 이상 안내해야 합니다 (시행령 제23조 제2항). "
                    "서비스 UI 또는 다운로드 안내 여부를 확인하세요."
                )

        # 워터마크만 있는 경우 (FOUND but invisible) → WARNING (탐지 불확실)
        else:
            triggered.append("R-02")
            verdict = Verdict.WARNING
            recommendation = (
                "워터마크가 탐지됐으나 탐지 신뢰도가 낮습니다. 추가 표시 방법을 권장합니다."
            )

        # R-07: 딥페이크 강화 표시 검증
        if ctx.is_deepfake_service is True and not visible_found:
            failing.append("R-07B")
            verdict = Verdict.NON_COMPLIANT
            recommendation = (
                "딥페이크 콘텐츠에는 사람이 명확히 인식할 수 있는 표시 방법만 허용됩니다\n"
                "(기계 판독 방식 단독 불가). 이미지 내 가시 라벨('AI 생성' 등)을 추가하세요."
            )
        elif ctx.is_deepfake_service is None and invisible_found and not visible_found:
            triggered.append("R-07C")
            if verdict == Verdict.COMPLIANT:
                verdict = Verdict.WARNING
                recommendation += (
                    "\n딥페이크 서비스 여부를 확인할 수 없습니다. "
                    "딥페이크 콘텐츠라면 가시 라벨이 필수입니다 (R-07)."
                )

        # R-06: 강건성 생존율 미달 → WARNING
        if robustness and verdict != Verdict.NON_COMPLIANT:
            low = {k: v for k, v in robustness.items() if v < self.robustness_threshold}
            if low:
                triggered.append("R-06")
                if verdict == Verdict.COMPLIANT:
                    verdict = Verdict.WARNING
                low_str = ", ".join(f"{k}={v:.0%}" for k, v in low.items())
                recommendation += (
                    f"\n표시 강건성이 낮습니다 (생존율 미달: {low_str}). "
                    "더 강건한 표시 방식 또는 복수 표시를 권장합니다 (R-06)."
                )

        return RuleVerdict(
            verdict=verdict,
            triggered_rules=triggered,
            failing_rules=failing,
            recommendation=recommendation,
        )

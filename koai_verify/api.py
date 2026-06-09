"""W12 — 공개 Python SDK API.

고수준 verify() 함수. CLI·JS SDK·웹 플레이그라운드 모두 이 함수를 사용한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from koai_verify.detectors.c2pa_detector import C2PADetector
from koai_verify.detectors.exif_detector import EXIFDetector
from koai_verify.detectors.ocr_detector import OCRDetector
from koai_verify.detectors.watermark_detector import WatermarkDetector
from koai_verify.pipeline import load_from_path
from koai_verify.report.formatter import VerificationReport
from koai_verify.robustness.harness import run_battery
from koai_verify.rules.engine import RuleEngine, aggregate_detections
from koai_verify.rules.models import VerificationContext

_DETECTORS = [C2PADetector(), EXIFDetector(), OCRDetector(), WatermarkDetector()]
_RULE_ENGINE = RuleEngine()


def verify(
    image_path: Union[str, Path],
    *,
    robustness: bool = False,
    context: VerificationContext | None = None,
) -> VerificationReport:
    """이미지를 검증하고 판정 리포트를 반환한다.

    Args:
        image_path: 검증할 이미지 파일 경로 (URL 금지 — SSRF 방지).
        robustness: True 이면 변형 배터리를 실행해 생존율을 리포트에 포함한다.
        context: 서비스 배포 컨텍스트. R-03 판정에 영향. None 이면 컨텍스트 불명.

    Returns:
        VerificationReport — 판정 결과, 탐지 결과, 강건성, 권고문 포함.

    Raises:
        ImageLoadError: 파일이 없거나 지원하지 않는 포맷.
    """
    img = load_from_path(image_path)
    outputs = [det.detect_safe(img.image_bytes) for det in _DETECTORS]

    robustness_dict: dict[str, float] = {}
    if robustness:
        for det in _DETECTORS:
            report = run_battery(img.image_bytes, det)
            robustness_dict.update(report.to_robustness_dict())

    detections = aggregate_detections(outputs)
    rule_verdict = _RULE_ENGINE.evaluate(detections, context=context, robustness=robustness_dict or None)

    return VerificationReport.from_rule_verdict(
        image_sha256=f"sha256:{img.sha256}",
        rule_verdict=rule_verdict,
        detections=detections,
        robustness=robustness_dict,
    )

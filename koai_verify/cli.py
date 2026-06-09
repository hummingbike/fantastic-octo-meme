"""W11 — CLI v0.

koai-verify <image> [--format json|summary] [--robustness]

종료 코드:
  0  COMPLIANT
  1  NON_COMPLIANT
  2  WARNING
  3  UNKNOWN
  10 입력 오류 (파일 없음, 포맷 미지원 등)
"""

from __future__ import annotations

import sys

import click

from koai_verify.detectors.c2pa_detector import C2PADetector
from koai_verify.detectors.exif_detector import EXIFDetector
from koai_verify.detectors.ocr_detector import OCRDetector
from koai_verify.detectors.watermark_detector import WatermarkDetector
from koai_verify.pipeline import ImageLoadError, load_from_path
from koai_verify.report.formatter import VerificationReport
from koai_verify.robustness.harness import run_battery
from koai_verify.rules.engine import RuleEngine, aggregate_detections

_DETECTORS = [C2PADetector(), EXIFDetector(), OCRDetector(), WatermarkDetector()]
_RULE_ENGINE = RuleEngine()

_EXIT_CODES = {
    "COMPLIANT": 0,
    "NON_COMPLIANT": 1,
    "WARNING": 2,
    "UNKNOWN": 3,
}


@click.command()
@click.argument("image_path", metavar="IMAGE")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "summary"], case_sensitive=False),
    default="json",
    show_default=True,
    help="출력 형식: json (기본) 또는 사람 읽기용 summary.",
)
@click.option(
    "--robustness",
    is_flag=True,
    default=False,
    help="강건성 배터리 실행 후 생존율을 리포트에 포함한다.",
)
def main(image_path: str, output_format: str, robustness: bool) -> None:
    """한국 AI 기본법 제31조 표시 의무 검증.

    IMAGE 파일을 검증하고 판정 결과를 출력한다.
    """
    try:
        img = load_from_path(image_path)
    except ImageLoadError as e:
        click.echo(f"오류: {e}", err=True)
        sys.exit(10)

    outputs = [det.detect_safe(img.image_bytes) for det in _DETECTORS]

    robustness_dict: dict[str, float] = {}
    if robustness:
        for det in _DETECTORS:
            report = run_battery(img.image_bytes, det)
            robustness_dict.update(report.to_robustness_dict())

    detections = aggregate_detections(outputs)
    rule_verdict = _RULE_ENGINE.evaluate(detections, robustness=robustness_dict or None)

    vreport = VerificationReport.from_rule_verdict(
        image_sha256=f"sha256:{img.sha256}",
        rule_verdict=rule_verdict,
        detections=detections,
        robustness=robustness_dict,
    )

    if output_format == "summary":
        click.echo(vreport.to_summary())
    else:
        click.echo(vreport.to_json())

    sys.exit(_EXIT_CODES.get(vreport.verdict, 3))

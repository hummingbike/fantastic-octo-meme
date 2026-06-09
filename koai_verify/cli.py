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

from koai_verify.api import verify
from koai_verify.pipeline import ImageLoadError

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
        vreport = verify(image_path, robustness=robustness)
    except ImageLoadError as e:
        click.echo(f"오류: {e}", err=True)
        sys.exit(10)

    if output_format == "summary":
        click.echo(vreport.to_summary())
    else:
        click.echo(vreport.to_json())

    sys.exit(_EXIT_CODES.get(vreport.verdict, 3))

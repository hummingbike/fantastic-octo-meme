"""W22 — 공유 가능한 판정 배지 (SVG).

shields.io 스타일의 정적 flat SVG 배지를 자체 생성한다. 외부 호스팅 의존이
없고, 판정 결과(verdict) 텍스트만 노출한다 — 원본 이미지 데이터는 포함하지
않는다 (CLAUDE.md: 판정 리포트에 원본 이미지 데이터 포함 금지).
"""

from __future__ import annotations

_VERDICT_COLORS: dict[str, str] = {
    "COMPLIANT": "#4c1",
    "NON_COMPLIANT": "#e05d44",
    "WARNING": "#dfb317",
    "UNKNOWN": "#9f9f9f",
}

_CHAR_WIDTH_PX = 7  # Verdana 11px 기준 문자당 근사 너비
_PADDING_PX = 10
_HEIGHT_PX = 20


def badge_color(verdict: str) -> str:
    """판정 결과에 대응하는 배지 색상(hex)을 반환한다. 알 수 없는 값은 UNKNOWN 색상."""
    return _VERDICT_COLORS.get(verdict, _VERDICT_COLORS["UNKNOWN"])


def _segment_width(text: str) -> int:
    return len(text) * _CHAR_WIDTH_PX + _PADDING_PX


def generate_badge_svg(verdict: str, label: str = "KoAI-Verify") -> str:
    """verdict를 나타내는 shields.io 스타일 flat SVG 배지 문자열을 반환한다.

    알 수 없는 verdict 값은 UNKNOWN과 동일한 회색으로 표시한다 (배지가 항상
    유효한 이미지를 반환하도록 — README/소셜 임베드에서 깨진 이미지 방지).
    """
    color = badge_color(verdict)
    label_width = _segment_width(label)
    value_width = _segment_width(verdict)
    total_width = label_width + value_width

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="{_HEIGHT_PX}" \
role="img" aria-label="{label}: {verdict}">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_width}" height="{_HEIGHT_PX}" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="{_HEIGHT_PX}" fill="#555"/>
    <rect x="{label_width}" width="{value_width}" height="{_HEIGHT_PX}" fill="{color}"/>
    <rect width="{total_width}" height="{_HEIGHT_PX}" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,sans-serif" font-size="11">
    <text x="{label_width / 2}" y="14">{label}</text>
    <text x="{label_width + value_width / 2}" y="14">{verdict}</text>
  </g>
</svg>"""

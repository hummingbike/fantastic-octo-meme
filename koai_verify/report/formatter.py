"""W10 — 판정 리포트 포맷터.

VerificationReport: 판정 결과를 JSON + 사람 읽기용 요약으로 출력한다.

보안 제약 (CLAUDE.md):
  - 원본 이미지 데이터 포함 금지 — sha256 해시/경로만 사용
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from koai_verify.rules.models import RuleVerdict, Verdict


@dataclass
class VerificationReport:
    """AI 생성 표시 검증 판정 리포트.

    리포트에는 원본 이미지 데이터를 포함하지 않는다 (sha256 해시만 기록).
    """

    image_sha256: str
    """원본 이미지 sha256 식별자 ("sha256:<hex>" 형식)."""

    verdict: str
    """판정 결과: COMPLIANT / NON_COMPLIANT / WARNING / UNKNOWN."""

    triggered_rules: list[str] = field(default_factory=list)
    """판정에 기여한 규칙 ID (R-01~R-07)."""

    failing_rules: list[str] = field(default_factory=list)
    """불충족을 유발한 규칙 ID."""

    detections: dict[str, str] = field(default_factory=dict)
    """탐지기별 결과: {"c2pa": "FOUND", "exif": "NOT_FOUND", ...}"""

    robustness: dict[str, float] = field(default_factory=dict)
    """탐지기별 생존율: {"exif": 0.4, ...}. 측정 안 했으면 빈 dict."""

    recommendation: str = ""
    """사람이 읽는 조치 권고문."""

    timestamp: str = ""
    """리포트 생성 시각 (ISO 8601 UTC)."""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()

    # ------------------------------------------------------------------
    # JSON 직렬화 / 역직렬화
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """JSON 직렬화용 dict 반환 (PLAN.md §W10 포맷)."""
        return {
            "image": self.image_sha256,
            "verdict": self.verdict,
            "triggered_rules": self.triggered_rules,
            "failing_rules": self.failing_rules,
            "detections": self.detections,
            "robustness": self.robustness,
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
        }

    def to_json(self, indent: int = 2) -> str:
        """JSON 문자열 반환."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "VerificationReport":
        """dict 에서 VerificationReport 를 복원한다."""
        return cls(
            image_sha256=data["image"],
            verdict=data["verdict"],
            triggered_rules=data.get("triggered_rules", []),
            failing_rules=data.get("failing_rules", []),
            detections=data.get("detections", {}),
            robustness=data.get("robustness", {}),
            recommendation=data.get("recommendation", ""),
            timestamp=data.get("timestamp", ""),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "VerificationReport":
        """JSON 문자열에서 VerificationReport 를 복원한다."""
        return cls.from_dict(json.loads(json_str))

    # ------------------------------------------------------------------
    # 팩토리 — RuleVerdict 로부터 생성
    # ------------------------------------------------------------------

    @classmethod
    def from_rule_verdict(
        cls,
        image_sha256: str,
        rule_verdict: RuleVerdict,
        detections: dict[str, str],
        robustness: Optional[dict[str, float]] = None,
        timestamp: Optional[str] = None,
    ) -> "VerificationReport":
        """RuleVerdict + 탐지 결과로 VerificationReport 를 생성한다.

        Args:
            image_sha256: 이미지 sha256 식별자.
            rule_verdict: RuleEngine.evaluate() 결과.
            detections: 탐지기별 결과 dict.
            robustness: 탐지기별 생존율 dict (없으면 빈 dict).
            timestamp: 명시적 타임스탬프 (None 이면 현재 시각).
        """
        return cls(
            image_sha256=image_sha256,
            verdict=rule_verdict.verdict.value,
            triggered_rules=list(rule_verdict.triggered_rules),
            failing_rules=list(rule_verdict.failing_rules),
            detections=detections,
            robustness=robustness or {},
            recommendation=rule_verdict.recommendation,
            timestamp=timestamp or _now_iso(),
        )

    # ------------------------------------------------------------------
    # 사람 읽기용 요약
    # ------------------------------------------------------------------

    def to_summary(self) -> str:
        """한국어 사람 읽기용 판정 요약 문자열을 반환한다."""
        lines: list[str] = [
            "=== KoAI-Verify 판정 리포트 ===",
            f"이미지:      {self.image_sha256}",
            f"판정:        {_verdict_ko(self.verdict)}",
        ]

        if self.triggered_rules or self.failing_rules:
            rule_list = self.triggered_rules + self.failing_rules
            lines.append(f"관련 규칙:   {', '.join(rule_list)}")

        if self.detections:
            lines.append("탐지 결과:")
            for name, result in self.detections.items():
                lines.append(f"  {name:<12} {_result_ko(result)}")

        if self.robustness:
            lines.append("강건성:")
            for name, rate in self.robustness.items():
                lines.append(f"  {name:<12} 생존율 {rate:.0%}")

        if self.recommendation:
            lines.append("권고사항:")
            for line in self.recommendation.strip().splitlines():
                lines.append(f"  {line}")

        lines.append(f"생성 시각:   {self.timestamp}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 편의 속성
    # ------------------------------------------------------------------

    def is_compliant(self) -> bool:
        return self.verdict == Verdict.COMPLIANT.value

    def is_non_compliant(self) -> bool:
        return self.verdict == Verdict.NON_COMPLIANT.value

    def has_warnings(self) -> bool:
        return self.verdict == Verdict.WARNING.value


# ---------------------------------------------------------------------------
# 공개 헬퍼
# ---------------------------------------------------------------------------


def format_report(
    image_sha256: str,
    rule_verdict: RuleVerdict,
    detections: dict[str, str],
    robustness: Optional[dict[str, float]] = None,
    timestamp: Optional[str] = None,
) -> VerificationReport:
    """RuleVerdict 를 받아 VerificationReport 를 생성하는 단축 함수."""
    return VerificationReport.from_rule_verdict(
        image_sha256=image_sha256,
        rule_verdict=rule_verdict,
        detections=detections,
        robustness=robustness,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# 내부 유틸리티
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_VERDICT_KO: dict[str, str] = {
    "COMPLIANT": "충족 (COMPLIANT)",
    "NON_COMPLIANT": "불충족 (NON_COMPLIANT)",
    "WARNING": "경고 (WARNING)",
    "UNKNOWN": "판정불가 (UNKNOWN)",
}

_RESULT_KO: dict[str, str] = {
    "FOUND": "발견",
    "NOT_FOUND": "미발견",
    "UNKNOWN": "판정불가",
}


def _verdict_ko(verdict: str) -> str:
    return _VERDICT_KO.get(verdict, verdict)


def _result_ko(result: str) -> str:
    return _RESULT_KO.get(result, result)

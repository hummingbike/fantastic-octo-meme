"""W5 — 룰 엔진 데이터 모델.

한국 AI 기본법 제31조 판정에 사용되는 Verdict, VerificationContext, RuleVerdict.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    """판정 결과 열거형 (제31조 컴플라이언스)."""

    COMPLIANT = "COMPLIANT"          # 제31조 충족
    NON_COMPLIANT = "NON_COMPLIANT"  # 명백한 불충족
    WARNING = "WARNING"              # 충족 가능성 있으나 컨텍스트 불명 또는 강건성 미달
    UNKNOWN = "UNKNOWN"              # 판정 불가 (탐지 결과 부족)


@dataclass
class VerificationContext:
    """검증 컨텍스트 — 서비스 배포 환경 정보.

    이미지 단독 검증 시에는 모두 None.
    API 호출 시 서비스 운영자가 제공.
    """

    is_external_distribution: bool | None = None
    """True = 외부 배포(다운로드·공유), False = 서비스 내 사용, None = 불명."""

    download_notice_confirmed: bool | None = None
    """다운로드/배포 시 '1회 이상 안내' 제공 여부. None = 확인 불가."""

    is_deepfake_service: bool | None = None
    """딥페이크 생성 서비스 여부. None = 불명 (R-07 경고 트리거)."""

    is_artistic_work: bool | None = None
    """예술적·창의적 표현물 여부 (제31조 제3항 단서). None = 불명."""


@dataclass
class RuleVerdict:
    """룰 엔진 판정 결과."""

    verdict: Verdict
    triggered_rules: list[str] = field(default_factory=list)
    """판정에 기여한 규칙 ID (R-01~R-07)."""

    failing_rules: list[str] = field(default_factory=list)
    """불충족을 유발한 규칙 ID."""

    recommendation: str = ""
    """사람이 읽는 조치 권고문."""

    def is_compliant(self) -> bool:
        return self.verdict == Verdict.COMPLIANT

    def is_non_compliant(self) -> bool:
        return self.verdict == Verdict.NON_COMPLIANT

    def has_warnings(self) -> bool:
        return self.verdict == Verdict.WARNING

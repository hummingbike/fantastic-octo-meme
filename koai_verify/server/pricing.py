"""W21 — 사용량 기반 가격 가설.

PRD §3.5(호스팅 API) 무료 티어(오픈 SDK) ↔ 유료 티어(호스팅·대량·리포트 보관)
경계 가설을 코드로 표현한다. 실제 과금은 아직 붙지 않으며, 외부 통합 파트너의
실사용 데이터(W24)로 한도·가격을 재보정하기 전까지의 **가설값**이다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from koai_verify.server.usage import UsageStats


class PricingTier(str, Enum):
    """가격 티어. 값이 클수록 한도가 넓다."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class TierLimits:
    """티어별 한도·가격 가설."""

    tier: PricingTier
    monthly_request_limit: Optional[int]  # None = 무제한
    max_image_bytes: int
    report_retention_days: int
    price_usd_per_month: float
    overage_usd_per_request: float  # 한도 초과 1건당 추가 과금


# 가격 가설 — docs/pricing_hypothesis.md 참조. 한도 순서대로 정렬되어 있으며,
# classify_tier()는 이 순서를 그대로 순회해 첫 번째로 맞는 티어를 고른다.
TIER_LIMITS: dict[PricingTier, TierLimits] = {
    PricingTier.FREE: TierLimits(
        tier=PricingTier.FREE,
        monthly_request_limit=500,
        max_image_bytes=10 * 1024 * 1024,
        report_retention_days=7,
        price_usd_per_month=0.0,
        overage_usd_per_request=0.0,
    ),
    PricingTier.PRO: TierLimits(
        tier=PricingTier.PRO,
        monthly_request_limit=20_000,
        max_image_bytes=50 * 1024 * 1024,
        report_retention_days=90,
        price_usd_per_month=49.0,
        overage_usd_per_request=0.005,
    ),
    PricingTier.ENTERPRISE: TierLimits(
        tier=PricingTier.ENTERPRISE,
        monthly_request_limit=None,
        max_image_bytes=50 * 1024 * 1024,
        report_retention_days=365,
        price_usd_per_month=499.0,
        overage_usd_per_request=0.0,
    ),
}

_TIER_ORDER: tuple[PricingTier, ...] = (PricingTier.FREE, PricingTier.PRO, PricingTier.ENTERPRISE)


def classify_tier(monthly_requests: int) -> PricingTier:
    """월간 요청 수를 초과 과금 없이 수용하는 가장 저렴한 티어를 반환한다."""
    if monthly_requests < 0:
        raise ValueError("monthly_requests must be >= 0")

    for tier in _TIER_ORDER:
        limit = TIER_LIMITS[tier].monthly_request_limit
        if limit is None or monthly_requests <= limit:
            return tier
    return PricingTier.ENTERPRISE


def compute_overage(monthly_requests: int, tier: PricingTier) -> int:
    """주어진 티어 한도를 초과한 요청 수 (한도 내면 0)."""
    limit = TIER_LIMITS[tier].monthly_request_limit
    if limit is None:
        return 0
    return max(0, monthly_requests - limit)


def estimate_monthly_cost(monthly_requests: int, tier: Optional[PricingTier] = None) -> float:
    """월 비용 추정 = 티어 기본가 + 초과 요청 × 초과 단가.

    tier가 None이면 classify_tier()로 가장 저렴하게 맞는 티어를 자동 선택한다
    (이 경우 정의상 초과분이 없어 기본가만 반환된다).
    """
    if tier is None:
        tier = classify_tier(monthly_requests)

    limits = TIER_LIMITS[tier]
    overage = compute_overage(monthly_requests, tier)
    return limits.price_usd_per_month + overage * limits.overage_usd_per_request


def usage_to_pricing_recommendation(stats: UsageStats) -> dict:
    """UsageStats(누적 사용량)를 가격 가설에 대조해 추천 티어·비용을 산출한다.

    UsageTracker는 호출 시점부터의 누적치를 담으므로, 여기서는 그 누적
    요청 수를 그대로 "이번 정산 주기 요청 수"로 취급한다.
    """
    requests = stats.total_requests
    tier = classify_tier(requests)
    return {
        "monthly_requests": requests,
        "recommended_tier": tier.value,
        "overage_requests": compute_overage(requests, tier),
        "estimated_cost_usd": estimate_monthly_cost(requests, tier),
    }


def get_tier_table() -> list[dict]:
    """가격 테이블을 API/문서에서 노출할 수 있는 직렬화 가능한 형태로 반환한다."""
    return [
        {
            "tier": limits.tier.value,
            "monthly_request_limit": limits.monthly_request_limit,
            "max_image_bytes": limits.max_image_bytes,
            "report_retention_days": limits.report_retention_days,
            "price_usd_per_month": limits.price_usd_per_month,
            "overage_usd_per_request": limits.overage_usd_per_request,
        }
        for limits in (TIER_LIMITS[t] for t in _TIER_ORDER)
    ]

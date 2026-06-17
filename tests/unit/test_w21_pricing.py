"""W21 — 사용량 기반 가격 가설: pricing 모듈, /v0/pricing 엔드포인트, 문서 검증."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest

_ROOT = Path(__file__).parent.parent.parent
_PRICING_DOC = _ROOT / "docs" / "pricing_hypothesis.md"
_PRICING_MOD = _ROOT / "koai_verify" / "server" / "pricing.py"


# ─────────────────────────────────────────────────────────────────────────────
# Task 1: koai_verify/server/pricing.py — 티어 정의·분류·과금 계산
# ─────────────────────────────────────────────────────────────────────────────


class TestPricingModuleStructure:
    def test_pricing_module_exists(self):
        assert _PRICING_MOD.exists()

    def test_pricing_module_nonempty(self):
        assert len(_PRICING_MOD.read_text(encoding="utf-8")) > 500

    def test_module_imports_cleanly(self):
        from koai_verify.server.pricing import TIER_LIMITS, PricingTier

        assert PricingTier is not None
        assert TIER_LIMITS is not None


class TestTierLimits:
    def test_three_tiers_defined(self):
        from koai_verify.server.pricing import TIER_LIMITS, PricingTier

        assert set(TIER_LIMITS.keys()) == {
            PricingTier.FREE,
            PricingTier.PRO,
            PricingTier.ENTERPRISE,
        }

    def test_free_tier_is_zero_cost(self):
        from koai_verify.server.pricing import TIER_LIMITS, PricingTier

        assert TIER_LIMITS[PricingTier.FREE].price_usd_per_month == 0.0

    def test_tiers_have_increasing_request_limits(self):
        from koai_verify.server.pricing import TIER_LIMITS, PricingTier

        free_limit = TIER_LIMITS[PricingTier.FREE].monthly_request_limit
        pro_limit = TIER_LIMITS[PricingTier.PRO].monthly_request_limit
        assert free_limit < pro_limit

    def test_enterprise_has_no_request_limit(self):
        from koai_verify.server.pricing import TIER_LIMITS, PricingTier

        assert TIER_LIMITS[PricingTier.ENTERPRISE].monthly_request_limit is None

    def test_tiers_have_increasing_prices(self):
        from koai_verify.server.pricing import TIER_LIMITS, PricingTier

        free_price = TIER_LIMITS[PricingTier.FREE].price_usd_per_month
        pro_price = TIER_LIMITS[PricingTier.PRO].price_usd_per_month
        ent_price = TIER_LIMITS[PricingTier.ENTERPRISE].price_usd_per_month
        assert free_price < pro_price < ent_price

    def test_tiers_have_increasing_retention(self):
        from koai_verify.server.pricing import TIER_LIMITS, PricingTier

        free_days = TIER_LIMITS[PricingTier.FREE].report_retention_days
        pro_days = TIER_LIMITS[PricingTier.PRO].report_retention_days
        ent_days = TIER_LIMITS[PricingTier.ENTERPRISE].report_retention_days
        assert free_days < pro_days < ent_days


class TestClassifyTier:
    def test_zero_requests_is_free(self):
        from koai_verify.server.pricing import PricingTier, classify_tier

        assert classify_tier(0) == PricingTier.FREE

    def test_at_free_limit_is_free(self):
        from koai_verify.server.pricing import TIER_LIMITS, PricingTier, classify_tier

        limit = TIER_LIMITS[PricingTier.FREE].monthly_request_limit
        assert classify_tier(limit) == PricingTier.FREE

    def test_just_above_free_limit_is_pro(self):
        from koai_verify.server.pricing import TIER_LIMITS, PricingTier, classify_tier

        limit = TIER_LIMITS[PricingTier.FREE].monthly_request_limit
        assert classify_tier(limit + 1) == PricingTier.PRO

    def test_at_pro_limit_is_pro(self):
        from koai_verify.server.pricing import TIER_LIMITS, PricingTier, classify_tier

        limit = TIER_LIMITS[PricingTier.PRO].monthly_request_limit
        assert classify_tier(limit) == PricingTier.PRO

    def test_just_above_pro_limit_is_enterprise(self):
        from koai_verify.server.pricing import TIER_LIMITS, PricingTier, classify_tier

        limit = TIER_LIMITS[PricingTier.PRO].monthly_request_limit
        assert classify_tier(limit + 1) == PricingTier.ENTERPRISE

    def test_huge_volume_is_enterprise(self):
        from koai_verify.server.pricing import PricingTier, classify_tier

        assert classify_tier(10_000_000) == PricingTier.ENTERPRISE

    def test_negative_requests_raises(self):
        from koai_verify.server.pricing import classify_tier

        with pytest.raises(ValueError):
            classify_tier(-1)


class TestComputeOverage:
    def test_no_overage_within_limit(self):
        from koai_verify.server.pricing import PricingTier, compute_overage

        assert compute_overage(100, PricingTier.FREE) == 0

    def test_overage_above_free_limit(self):
        from koai_verify.server.pricing import TIER_LIMITS, PricingTier, compute_overage

        limit = TIER_LIMITS[PricingTier.FREE].monthly_request_limit
        assert compute_overage(limit + 50, PricingTier.FREE) == 50

    def test_enterprise_never_has_overage(self):
        from koai_verify.server.pricing import PricingTier, compute_overage

        assert compute_overage(10_000_000, PricingTier.ENTERPRISE) == 0


class TestEstimateMonthlyCost:
    def test_free_tier_zero_cost_within_limit(self):
        from koai_verify.server.pricing import PricingTier, estimate_monthly_cost

        assert estimate_monthly_cost(100, PricingTier.FREE) == 0.0

    def test_pro_tier_base_cost_within_limit(self):
        from koai_verify.server.pricing import TIER_LIMITS, PricingTier, estimate_monthly_cost

        cost = estimate_monthly_cost(1000, PricingTier.PRO)
        assert cost == TIER_LIMITS[PricingTier.PRO].price_usd_per_month

    def test_pro_tier_overage_adds_cost(self):
        from koai_verify.server.pricing import TIER_LIMITS, PricingTier, estimate_monthly_cost

        limits = TIER_LIMITS[PricingTier.PRO]
        over_requests = limits.monthly_request_limit + 1000
        cost = estimate_monthly_cost(over_requests, PricingTier.PRO)
        expected = limits.price_usd_per_month + 1000 * limits.overage_usd_per_request
        assert cost == pytest.approx(expected)

    def test_tier_none_autoselects_cheapest_fit(self):
        from koai_verify.server.pricing import estimate_monthly_cost

        assert estimate_monthly_cost(100) == 0.0
        assert estimate_monthly_cost(50_000) > 0.0

    def test_enterprise_flat_rate_regardless_of_volume(self):
        from koai_verify.server.pricing import TIER_LIMITS, PricingTier, estimate_monthly_cost

        flat = TIER_LIMITS[PricingTier.ENTERPRISE].price_usd_per_month
        assert estimate_monthly_cost(1_000_000, PricingTier.ENTERPRISE) == flat
        assert estimate_monthly_cost(100_000_000, PricingTier.ENTERPRISE) == flat


class TestUsageToPricingRecommendation:
    def _stats(self, total_requests: int):
        from koai_verify.server.usage import UsageStats

        return UsageStats(total_requests=total_requests, total_image_bytes=0, verdict_counts={}, records=[])

    def test_returns_required_keys(self):
        from koai_verify.server.pricing import usage_to_pricing_recommendation

        rec = usage_to_pricing_recommendation(self._stats(10))
        for key in ("monthly_requests", "recommended_tier", "overage_requests", "estimated_cost_usd"):
            assert key in rec

    def test_zero_usage_recommends_free(self):
        from koai_verify.server.pricing import usage_to_pricing_recommendation

        rec = usage_to_pricing_recommendation(self._stats(0))
        assert rec["recommended_tier"] == "free"
        assert rec["estimated_cost_usd"] == 0.0

    def test_high_usage_recommends_paid_tier(self):
        from koai_verify.server.pricing import usage_to_pricing_recommendation

        rec = usage_to_pricing_recommendation(self._stats(100_000))
        assert rec["recommended_tier"] in ("pro", "enterprise")
        assert rec["estimated_cost_usd"] > 0.0


class TestGetTierTable:
    def test_returns_three_entries(self):
        from koai_verify.server.pricing import get_tier_table

        table = get_tier_table()
        assert len(table) == 3

    def test_entries_are_dicts_with_required_fields(self):
        from koai_verify.server.pricing import get_tier_table

        required = {
            "tier",
            "monthly_request_limit",
            "max_image_bytes",
            "report_retention_days",
            "price_usd_per_month",
            "overage_usd_per_request",
        }
        for entry in get_tier_table():
            assert required.issubset(entry.keys())

    def test_order_is_free_pro_enterprise(self):
        from koai_verify.server.pricing import get_tier_table

        tiers = [entry["tier"] for entry in get_tier_table()]
        assert tiers == ["free", "pro", "enterprise"]


# ─────────────────────────────────────────────────────────────────────────────
# Task 2: GET /v0/pricing 엔드포인트
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def dev_mode_env() -> Generator[None, None, None]:
    with patch.dict(os.environ, {"KOAI_DEV_MODE": "true", "KOAI_API_KEYS": ""}):
        yield


@pytest.fixture()
def client(dev_mode_env):
    from fastapi.testclient import TestClient

    from koai_verify.server.app import app
    from koai_verify.server.usage import UsageTracker, set_tracker

    set_tracker(UsageTracker())
    with TestClient(app) as c:
        yield c


class TestPricingEndpoint:
    def test_pricing_returns_200(self, client):
        resp = client.get("/v0/pricing")
        assert resp.status_code == 200

    def test_pricing_has_tiers_and_recommendation(self, client):
        body = client.get("/v0/pricing").json()
        assert "tiers" in body
        assert "recommendation" in body

    def test_pricing_tiers_has_three_entries(self, client):
        body = client.get("/v0/pricing").json()
        assert len(body["tiers"]) == 3

    def test_pricing_recommendation_reflects_usage(self, client):
        from koai_verify.server.usage import get_tracker

        get_tracker().record(image_size_bytes=100, verdict="COMPLIANT", api_key="k", duration_ms=1.0)
        body = client.get("/v0/pricing").json()
        assert body["recommendation"]["monthly_requests"] >= 1

    def test_pricing_requires_auth_when_keys_set(self):
        env = {k: v for k, v in os.environ.items() if k != "KOAI_DEV_MODE"}
        env["KOAI_API_KEYS"] = "testkey123"
        env["KOAI_DEV_MODE"] = "false"
        with patch.dict(os.environ, env, clear=True):
            from fastapi.testclient import TestClient

            from koai_verify.server.app import app

            with TestClient(app) as c:
                resp = c.get("/v0/pricing")
        assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# Task 3: docs/pricing_hypothesis.md
# ─────────────────────────────────────────────────────────────────────────────


class TestPricingHypothesisDocument:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return _PRICING_DOC.read_text(encoding="utf-8")

    def test_file_exists(self):
        assert _PRICING_DOC.exists()

    def test_is_nonempty(self, content: str):
        assert len(content) > 1000

    def test_starts_with_heading(self, content: str):
        assert content.startswith("#")

    def test_mentions_three_tiers(self, content: str):
        for tier in ("Free", "Pro", "Enterprise"):
            assert tier in content

    def test_has_background_section(self, content: str):
        assert "배경" in content

    def test_references_prd_section_3_5(self, content: str):
        assert "3.5" in content or "호스팅 API" in content

    def test_mentions_free_paid_boundary(self, content: str):
        assert "무료" in content and "유료" in content

    def test_references_pricing_module(self, content: str):
        assert "pricing.py" in content

    def test_has_basis_or_rationale_section(self, content: str):
        assert "근거" in content

    def test_has_limitations_section(self, content: str):
        assert "한계" in content

    def test_mentions_w24_validation_plan(self, content: str):
        assert "W24" in content

    def test_mentions_cli_sdk_remains_free(self, content: str):
        assert "pip install koai-verify" in content or "npm install" in content

    def test_no_hardcoded_personal_paths(self, content: str):
        assert "/Users/okestro" not in content

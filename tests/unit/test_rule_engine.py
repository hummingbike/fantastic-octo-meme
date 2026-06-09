"""W5 Task4 — 룰 엔진 단위 테스트.

R-01~R-07 판정 로직, Verdict, VerificationContext, RuleVerdict 검증.
"""
from __future__ import annotations

from koai_verify.rules import RuleEngine, RuleVerdict, Verdict, VerificationContext

# 공통 탐지 결과 상수
FOUND = "FOUND"
NOT_FOUND = "NOT_FOUND"
UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Verdict 모델
# ---------------------------------------------------------------------------

class TestVerdict:
    def test_four_values_exist(self):
        assert len(Verdict) == 4

    def test_compliant_value(self):
        assert Verdict.COMPLIANT == "COMPLIANT"

    def test_non_compliant_value(self):
        assert Verdict.NON_COMPLIANT == "NON_COMPLIANT"

    def test_warning_value(self):
        assert Verdict.WARNING == "WARNING"

    def test_unknown_value(self):
        assert Verdict.UNKNOWN == "UNKNOWN"

    def test_is_str_subclass(self):
        assert isinstance(Verdict.COMPLIANT, str)


# ---------------------------------------------------------------------------
# VerificationContext 기본값
# ---------------------------------------------------------------------------

class TestVerificationContext:
    def test_all_none_by_default(self):
        ctx = VerificationContext()
        assert ctx.is_external_distribution is None
        assert ctx.download_notice_confirmed is None
        assert ctx.is_deepfake_service is None
        assert ctx.is_artistic_work is None


# ---------------------------------------------------------------------------
# RuleVerdict 편의 메서드
# ---------------------------------------------------------------------------

class TestRuleVerdict:
    def test_is_compliant_true(self):
        rv = RuleVerdict(verdict=Verdict.COMPLIANT)
        assert rv.is_compliant()

    def test_is_non_compliant_true(self):
        rv = RuleVerdict(verdict=Verdict.NON_COMPLIANT)
        assert rv.is_non_compliant()

    def test_has_warnings_true(self):
        rv = RuleVerdict(verdict=Verdict.WARNING)
        assert rv.has_warnings()

    def test_is_compliant_false_for_warning(self):
        rv = RuleVerdict(verdict=Verdict.WARNING)
        assert not rv.is_compliant()


# ---------------------------------------------------------------------------
# R-05: 표시 전무 → NON_COMPLIANT
# ---------------------------------------------------------------------------

class TestR05NoMarking:
    engine = RuleEngine()

    def test_all_not_found_non_compliant(self):
        rv = self.engine.evaluate({"c2pa": NOT_FOUND, "exif": NOT_FOUND, "ocr": NOT_FOUND})
        assert rv.verdict == Verdict.NON_COMPLIANT

    def test_all_unknown_non_compliant(self):
        rv = self.engine.evaluate({"c2pa": UNKNOWN, "exif": UNKNOWN, "ocr": NOT_FOUND})
        assert rv.verdict == Verdict.NON_COMPLIANT

    def test_r05_in_failing_rules(self):
        rv = self.engine.evaluate({"c2pa": NOT_FOUND, "exif": NOT_FOUND, "ocr": NOT_FOUND})
        assert "R-05" in rv.failing_rules

    def test_empty_detections_non_compliant(self):
        rv = self.engine.evaluate({})
        assert rv.verdict == Verdict.NON_COMPLIANT

    def test_recommendation_not_empty(self):
        rv = self.engine.evaluate({})
        assert len(rv.recommendation) > 0


# ---------------------------------------------------------------------------
# R-04: 가시 라벨 → COMPLIANT
# ---------------------------------------------------------------------------

class TestR04VisibleLabel:
    engine = RuleEngine()

    def test_ocr_found_compliant(self):
        rv = self.engine.evaluate({"ocr": FOUND})
        assert rv.verdict == Verdict.COMPLIANT

    def test_r04_in_triggered_rules(self):
        rv = self.engine.evaluate({"ocr": FOUND})
        assert "R-04" in rv.triggered_rules

    def test_ocr_found_with_c2pa_also_compliant(self):
        rv = self.engine.evaluate({"c2pa": FOUND, "ocr": FOUND})
        assert rv.verdict == Verdict.COMPLIANT

    def test_ocr_found_no_r05(self):
        rv = self.engine.evaluate({"ocr": FOUND})
        assert "R-05" not in rv.failing_rules


# ---------------------------------------------------------------------------
# R-01/R-02 + R-03: 비가시 전용 컨텍스트 판정
# ---------------------------------------------------------------------------

class TestR03InvisibleOnly:
    engine = RuleEngine()

    def _ctx(self, notice: bool | None = None, external: bool | None = None) -> VerificationContext:
        return VerificationContext(
            download_notice_confirmed=notice,
            is_external_distribution=external,
        )

    def test_c2pa_only_context_unknown_warning(self):
        rv = self.engine.evaluate({"c2pa": FOUND}, context=self._ctx())
        assert rv.verdict == Verdict.WARNING
        assert "R-03C" in rv.triggered_rules

    def test_exif_only_context_unknown_warning(self):
        rv = self.engine.evaluate({"exif": FOUND}, context=self._ctx())
        assert rv.verdict == Verdict.WARNING

    def test_r01_triggered_for_c2pa(self):
        rv = self.engine.evaluate({"c2pa": FOUND})
        assert "R-01" in rv.triggered_rules

    def test_r02_triggered_for_exif(self):
        rv = self.engine.evaluate({"exif": FOUND})
        assert "R-02" in rv.triggered_rules

    def test_notice_confirmed_compliant(self):
        # 딥페이크 서비스가 아님을 명시해야 R-07C 미발동 → COMPLIANT
        ctx = VerificationContext(
            download_notice_confirmed=True,
            is_deepfake_service=False,
        )
        rv = self.engine.evaluate({"c2pa": FOUND}, context=ctx)
        assert rv.verdict == Verdict.COMPLIANT
        assert "R-03A" in rv.triggered_rules

    def test_no_notice_external_distribution_non_compliant(self):
        rv = self.engine.evaluate(
            {"exif": FOUND},
            context=self._ctx(notice=False, external=True),
        )
        assert rv.verdict == Verdict.NON_COMPLIANT
        assert "R-03B" in rv.failing_rules

    def test_no_notice_not_external_warning(self):
        rv = self.engine.evaluate(
            {"exif": FOUND},
            context=self._ctx(notice=False, external=False),
        )
        assert rv.verdict == Verdict.WARNING

    def test_no_context_warning(self):
        rv = self.engine.evaluate({"c2pa": FOUND})
        assert rv.verdict == Verdict.WARNING


# ---------------------------------------------------------------------------
# R-07: 딥페이크 강화 검증
# ---------------------------------------------------------------------------

class TestR07Deepfake:
    engine = RuleEngine()

    def test_deepfake_service_invisible_only_non_compliant(self):
        ctx = VerificationContext(is_deepfake_service=True)
        rv = self.engine.evaluate({"c2pa": FOUND}, context=ctx)
        assert rv.verdict == Verdict.NON_COMPLIANT
        assert "R-07B" in rv.failing_rules

    def test_deepfake_service_visible_label_compliant(self):
        ctx = VerificationContext(is_deepfake_service=True)
        rv = self.engine.evaluate({"ocr": FOUND}, context=ctx)
        assert rv.verdict == Verdict.COMPLIANT

    def test_deepfake_unknown_invisible_downgrades_to_warning(self):
        ctx = VerificationContext(
            is_deepfake_service=None,
            download_notice_confirmed=True,
        )
        rv = self.engine.evaluate({"c2pa": FOUND}, context=ctx)
        assert rv.verdict == Verdict.WARNING
        assert "R-07C" in rv.triggered_rules

    def test_deepfake_false_does_not_trigger_r07(self):
        ctx = VerificationContext(is_deepfake_service=False, download_notice_confirmed=True)
        rv = self.engine.evaluate({"c2pa": FOUND}, context=ctx)
        assert "R-07B" not in rv.failing_rules
        assert rv.verdict == Verdict.COMPLIANT


# ---------------------------------------------------------------------------
# R-06: 강건성 생존율 미달 → WARNING
# ---------------------------------------------------------------------------

class TestR06Robustness:
    engine = RuleEngine(robustness_threshold=0.70)

    def test_low_survival_downgrades_compliant_to_warning(self):
        robustness = {"c2pa": 0.50}
        rv = self.engine.evaluate(
            {"ocr": FOUND},
            robustness=robustness,
        )
        assert rv.verdict == Verdict.WARNING
        assert "R-06" in rv.triggered_rules

    def test_high_survival_keeps_compliant(self):
        robustness = {"c2pa": 0.85}
        rv = self.engine.evaluate({"ocr": FOUND}, robustness=robustness)
        assert rv.verdict == Verdict.COMPLIANT

    def test_r06_does_not_upgrade_non_compliant(self):
        rv = self.engine.evaluate(
            {"c2pa": NOT_FOUND, "exif": NOT_FOUND, "ocr": NOT_FOUND},
            robustness={"c2pa": 0.10},
        )
        assert rv.verdict == Verdict.NON_COMPLIANT

    def test_threshold_boundary_at_exactly_70pct_no_r06(self):
        robustness = {"c2pa": 0.70}
        rv = self.engine.evaluate({"ocr": FOUND}, robustness=robustness)
        # 0.70 == threshold → not strictly less than → R-06 미발동
        assert "R-06" not in rv.triggered_rules

    def test_custom_threshold(self):
        engine = RuleEngine(robustness_threshold=0.90)
        robustness = {"c2pa": 0.80}
        rv = engine.evaluate({"ocr": FOUND}, robustness=robustness)
        assert "R-06" in rv.triggered_rules

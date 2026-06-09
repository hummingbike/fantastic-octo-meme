"""W14 — 배치 분석기 단위 테스트.

run_batch_analysis() 와 데이터 모델을 검증한다.
실제 픽스처 이미지를 사용하며 mock 을 사용하지 않는다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent
SAMPLES_DIR = ROOT / "tests" / "fixtures" / "samples"


class TestToolVerifyResult:
    """ToolVerifyResult 데이터 모델 테스트."""

    def _make_result(self, verdicts, triggered_rules=None, is_placeholder=False, detections=None):
        from koai_verify.analysis.batch_runner import ToolVerifyResult

        return ToolVerifyResult(
            tool_name="test_tool",
            sample_count=len(verdicts),
            is_placeholder=is_placeholder,
            verdicts=verdicts,
            triggered_rules=triggered_rules or [[] for _ in verdicts],
            detections=detections or [{} for _ in verdicts],
            sns_survival={},
        )

    def test_dominant_verdict_single(self):
        r = self._make_result(["NON_COMPLIANT"])
        assert r.dominant_verdict() == "NON_COMPLIANT"

    def test_dominant_verdict_majority(self):
        r = self._make_result(["WARNING", "WARNING", "NON_COMPLIANT"])
        assert r.dominant_verdict() == "WARNING"

    def test_dominant_verdict_empty(self):
        r = self._make_result([])
        assert r.dominant_verdict() == "UNKNOWN"

    def test_gap_category_placeholder_is_unknown(self):
        r = self._make_result(["NON_COMPLIANT"], is_placeholder=True)
        assert r.gap_category() == "UNKNOWN"

    def test_gap_category_noncompliant_r05_is_no_marking(self):
        r = self._make_result(
            ["NON_COMPLIANT"],
            triggered_rules=[["R-05"]],
            is_placeholder=False,
        )
        assert r.gap_category() == "NO_MARKING"

    def test_gap_category_warning_is_invisible_only(self):
        r = self._make_result(
            ["WARNING"],
            triggered_rules=[["R-02", "R-03C"]],
        )
        assert r.gap_category() == "INVISIBLE_ONLY"

    def test_gap_category_compliant_is_detectable(self):
        r = self._make_result(
            ["COMPLIANT"],
            triggered_rules=[["R-04"]],
        )
        assert r.gap_category() == "DETECTABLE"

    def test_sns_mean_survival_no_measurements(self):
        from koai_verify.analysis.batch_runner import ToolVerifyResult

        r = ToolVerifyResult(
            tool_name="t",
            sample_count=1,
            is_placeholder=False,
            verdicts=["NON_COMPLIANT"],
            triggered_rules=[[]],
            detections=[{}],
            sns_survival={},
        )
        assert r.sns_mean_survival() == -1.0

    def test_sns_mean_survival_all_not_measurable(self):
        from koai_verify.analysis.batch_runner import ToolVerifyResult

        r = ToolVerifyResult(
            tool_name="t",
            sample_count=1,
            is_placeholder=False,
            verdicts=["NON_COMPLIANT"],
            triggered_rules=[[]],
            detections=[{}],
            sns_survival={"sns_instagram": -1.0, "sns_twitter": -1.0},
        )
        assert r.sns_mean_survival() == -1.0

    def test_sns_mean_survival_partial(self):
        from koai_verify.analysis.batch_runner import ToolVerifyResult

        r = ToolVerifyResult(
            tool_name="t",
            sample_count=1,
            is_placeholder=False,
            verdicts=["WARNING"],
            triggered_rules=[[]],
            detections=[{}],
            sns_survival={"sns_instagram": 0.0, "sns_twitter": 0.0},
        )
        assert r.sns_mean_survival() == pytest.approx(0.0)


class TestBatchAnalysisReport:
    """BatchAnalysisReport 데이터 모델 테스트."""

    def _make_report(self, tool_configs):
        """tool_configs: [(tool_name, verdicts, triggered_rules, is_placeholder)]"""
        from koai_verify.analysis.batch_runner import BatchAnalysisReport, ToolVerifyResult

        results = {}
        total = 0
        for tool_name, verdicts, triggered_rules, is_placeholder in tool_configs:
            results[tool_name] = ToolVerifyResult(
                tool_name=tool_name,
                sample_count=len(verdicts),
                is_placeholder=is_placeholder,
                verdicts=verdicts,
                triggered_rules=triggered_rules,
                detections=[{} for _ in verdicts],
                sns_survival={},
            )
            total += len(verdicts)
        return BatchAnalysisReport(
            analyzed_at="2026-08-31T00:00:00Z",
            total_samples=total,
            tool_results=results,
        )

    def test_gap_summary_returns_dict(self):
        report = self._make_report(
            [
                ("tool_a", ["NON_COMPLIANT"], [["R-05"]], False),
                ("tool_b", ["WARNING"], [["R-03C"]], False),
                ("tool_c", ["NON_COMPLIANT"], [[]], True),
            ]
        )
        summary = report.gap_summary()
        assert isinstance(summary, dict)
        assert "tool_a" in summary
        assert "tool_b" in summary
        assert "tool_c" in summary

    def test_gap_summary_placeholder_is_unknown(self):
        report = self._make_report([("drapart", ["NON_COMPLIANT"], [["R-05"]], True)])
        assert report.gap_summary()["drapart"] == "UNKNOWN"

    def test_gap_summary_no_marking_tool(self):
        report = self._make_report([("midjourney", ["NON_COMPLIANT", "NON_COMPLIANT"], [["R-05"], ["R-05"]], False)])
        assert report.gap_summary()["midjourney"] == "NO_MARKING"

    def test_gap_summary_invisible_only_tool(self):
        report = self._make_report(
            [("stable_diffusion", ["WARNING", "WARNING"], [["R-02", "R-03C"], ["R-02", "R-03C"]], False)]
        )
        assert report.gap_summary()["stable_diffusion"] == "INVISIBLE_ONLY"

    def test_tools_by_gap_structure(self):
        report = self._make_report(
            [
                ("mj", ["NON_COMPLIANT"], [["R-05"]], False),
                ("sd", ["WARNING"], [["R-03C"]], False),
                ("drapart", ["NON_COMPLIANT"], [["R-05"]], True),
            ]
        )
        by_gap = report.tools_by_gap()
        assert isinstance(by_gap, dict)
        assert "mj" in by_gap.get("NO_MARKING", [])
        assert "sd" in by_gap.get("INVISIBLE_ONLY", [])
        assert "drapart" in by_gap.get("UNKNOWN", [])

    def test_overall_noncompliant_rate_all(self):
        report = self._make_report([("t", ["NON_COMPLIANT", "NON_COMPLIANT"], [["R-05"], ["R-05"]], False)])
        assert report.overall_noncompliant_rate() == pytest.approx(1.0)

    def test_overall_noncompliant_rate_none(self):
        report = self._make_report([("t", ["COMPLIANT", "COMPLIANT"], [["R-04"], ["R-04"]], False)])
        assert report.overall_noncompliant_rate() == pytest.approx(0.0)

    def test_overall_noncompliant_rate_empty(self):
        from koai_verify.analysis.batch_runner import BatchAnalysisReport

        report = BatchAnalysisReport(analyzed_at="2026-01-01T00:00:00Z", total_samples=0)
        assert report.overall_noncompliant_rate() == pytest.approx(0.0)

    def test_comparison_with_catalog_keys(self):
        report = self._make_report(
            [
                ("midjourney", ["NON_COMPLIANT"], [["R-05"]], False),
                ("stable_diffusion", ["WARNING"], [["R-03C"]], False),
            ]
        )
        comparison = report.comparison_with_catalog()
        assert "midjourney" in comparison
        assert "stable_diffusion" in comparison

    def test_comparison_midjourney_predicted_no_marking(self):
        report = self._make_report([("midjourney", ["NON_COMPLIANT"], [["R-05"]], False)])
        comp = report.comparison_with_catalog()["midjourney"]
        assert comp["predicted_gap"] == "no_marking"
        assert comp["actual_gap"] == "NO_MARKING"

    def test_comparison_stable_diffusion_predicted_invisible(self):
        report = self._make_report([("stable_diffusion", ["WARNING"], [["R-03C"]], False)])
        comp = report.comparison_with_catalog()["stable_diffusion"]
        assert comp["predicted_gap"] == "invisible_only"
        assert comp["actual_gap"] == "INVISIBLE_ONLY"

    def test_comparison_placeholder_tool(self):
        report = self._make_report([("drapart", ["NON_COMPLIANT"], [[]], True)])
        comp = report.comparison_with_catalog()["drapart"]
        assert comp["is_placeholder"] is True
        assert comp["actual_gap"] == "UNKNOWN"

    def test_analyzed_at_is_set(self):
        report = self._make_report([("t", ["WARNING"], [[]], False)])
        assert report.analyzed_at


class TestRunBatchAnalysisWithFixtures:
    """실제 픽스처로 run_batch_analysis() 통합 테스트."""

    @pytest.fixture(scope="class")
    def report(self):
        from koai_verify.analysis.batch_runner import run_batch_analysis

        return run_batch_analysis(SAMPLES_DIR)

    def test_samples_dir_exists(self):
        assert SAMPLES_DIR.exists()

    def test_report_has_tool_results(self, report):
        assert len(report.tool_results) >= 5

    def test_report_has_stable_diffusion(self, report):
        assert "stable_diffusion" in report.tool_results

    def test_report_has_midjourney(self, report):
        assert "midjourney" in report.tool_results

    def test_report_has_comfyui(self, report):
        assert "comfyui" in report.tool_results

    def test_report_has_dalle3(self, report):
        assert "dalle3" in report.tool_results

    def test_report_total_samples_positive(self, report):
        assert report.total_samples > 0

    def test_stable_diffusion_verdict_is_warning(self, report):
        """SD 픽스처: EXIF AI 마킹 있음 + 컨텍스트 불명 → WARNING."""
        r = report.tool_results["stable_diffusion"]
        assert r.dominant_verdict() == "WARNING"

    def test_stable_diffusion_gap_is_invisible_only(self, report):
        r = report.tool_results["stable_diffusion"]
        assert r.gap_category() == "INVISIBLE_ONLY"

    def test_comfyui_verdict_is_warning(self, report):
        """ComfyUI 픽스처: EXIF Software='ComfyUI' → EXIF FOUND → WARNING."""
        r = report.tool_results["comfyui"]
        assert r.dominant_verdict() == "WARNING"

    def test_midjourney_verdict_is_noncompliant(self, report):
        """Midjourney 픽스처: 마킹 없음 → R-05 → NON_COMPLIANT."""
        r = report.tool_results["midjourney"]
        assert r.dominant_verdict() == "NON_COMPLIANT"

    def test_midjourney_gap_is_no_marking(self, report):
        r = report.tool_results["midjourney"]
        assert r.gap_category() == "NO_MARKING"

    def test_dalle3_verdict_is_noncompliant(self, report):
        r = report.tool_results["dalle3"]
        assert r.dominant_verdict() == "NON_COMPLIANT"

    def test_placeholder_tools_are_flagged(self, report):
        """드랩아트·GenApe·벨라·제디터는 플레이스홀더로 표시된다."""
        for tool in ("drapart", "genape", "vela", "jeditor"):
            if tool in report.tool_results:
                assert report.tool_results[tool].is_placeholder is True

    def test_placeholder_tools_gap_is_unknown(self, report):
        for tool in ("drapart", "genape", "vela", "jeditor"):
            if tool in report.tool_results:
                assert report.tool_results[tool].gap_category() == "UNKNOWN"

    def test_gap_summary_has_no_marking_tools(self, report):
        summary = report.gap_summary()
        no_marking_tools = [t for t, g in summary.items() if g == "NO_MARKING"]
        assert len(no_marking_tools) >= 2  # midjourney, dalle3

    def test_gap_summary_has_invisible_only_tools(self, report):
        summary = report.gap_summary()
        invisible_tools = [t for t, g in summary.items() if g == "INVISIBLE_ONLY"]
        assert len(invisible_tools) >= 1  # stable_diffusion

    def test_comparison_with_catalog_has_entries(self, report):
        comparison = report.comparison_with_catalog()
        assert len(comparison) >= 5

    def test_comparison_midjourney_matches_catalog(self, report):
        comp = report.comparison_with_catalog().get("midjourney", {})
        # midjourney catalog: NO_MARKING → actual: NO_MARKING → match=True
        if comp:
            assert comp["match"] is True

    def test_overall_noncompliant_rate_is_high(self, report):
        """대부분 샘플이 NON_COMPLIANT 이어야 한다 (법적 표시 미비)."""
        rate = report.overall_noncompliant_rate()
        # midjourney, dalle3, placeholder(NON_COMPLIANT로 검증됨)는 NON_COMPLIANT
        # SD/ComfyUI/Firefly는 WARNING
        assert rate >= 0.3  # 최소 30%는 NON_COMPLIANT


class TestMeasureSnsSurvival:
    """SNS 생존율 측정 헬퍼 테스트."""

    @pytest.fixture
    def sd_sample(self):
        p = SAMPLES_DIR / "stable_diffusion" / "stable_diffusion_01.jpg"
        pytest.skip_if_missing = not p.exists()
        if not p.exists():
            pytest.skip("stable_diffusion_01.jpg fixture missing")
        return p

    @pytest.fixture
    def plain_sample(self):
        p = SAMPLES_DIR / "midjourney" / "midjourney_01.jpg"
        if not p.exists():
            pytest.skip("midjourney_01.jpg fixture missing")
        return p

    def test_sd_sns_survival_returns_dict(self, sd_sample):
        from koai_verify.analysis.batch_runner import _measure_sns_survival

        result = _measure_sns_survival(sd_sample)
        assert isinstance(result, dict)

    def test_sd_sns_survival_has_sns_keys(self, sd_sample):
        from koai_verify.analysis.batch_runner import SNS_TRANSFORM_LABELS, _measure_sns_survival

        result = _measure_sns_survival(sd_sample)
        for label in SNS_TRANSFORM_LABELS:
            assert label in result

    def test_sd_sns_survival_values_valid(self, sd_sample):
        from koai_verify.analysis.batch_runner import _measure_sns_survival

        result = _measure_sns_survival(sd_sample)
        for v in result.values():
            # 0.0 (소거), 1.0 (생존), -1.0 (측정 불가)
            assert v in (0.0, 1.0, -1.0)

    def test_sd_sns_exif_stripped_by_sns(self, sd_sample):
        """SD 픽스처의 EXIF 는 SNS 재인코딩 후 소거된다."""
        from koai_verify.analysis.batch_runner import _measure_sns_survival

        result = _measure_sns_survival(sd_sample)
        # SNS 후 EXIF 소거 → 0.0 이어야 함
        for label, rate in result.items():
            if rate >= 0.0:
                assert rate == pytest.approx(0.0), f"{label}: 예상 0.0, 실제 {rate}"

    def test_plain_sns_survival_not_measurable(self, plain_sample):
        """마킹 없는 이미지는 모두 -1.0."""
        from koai_verify.analysis.batch_runner import _measure_sns_survival

        result = _measure_sns_survival(plain_sample)
        for v in result.values():
            assert v == pytest.approx(-1.0)


class TestSNSTransformLabels:
    """SNS_TRANSFORM_LABELS 상수 검증."""

    def test_has_four_sns_labels(self):
        from koai_verify.analysis.batch_runner import SNS_TRANSFORM_LABELS

        assert len(SNS_TRANSFORM_LABELS) == 4

    def test_instagram_in_labels(self):
        from koai_verify.analysis.batch_runner import SNS_TRANSFORM_LABELS

        assert "sns_instagram" in SNS_TRANSFORM_LABELS

    def test_twitter_in_labels(self):
        from koai_verify.analysis.batch_runner import SNS_TRANSFORM_LABELS

        assert "sns_twitter" in SNS_TRANSFORM_LABELS

    def test_kakao_chat_in_labels(self):
        from koai_verify.analysis.batch_runner import SNS_TRANSFORM_LABELS

        assert "sns_kakaotalk_chat" in SNS_TRANSFORM_LABELS

    def test_kakao_profile_in_labels(self):
        from koai_verify.analysis.batch_runner import SNS_TRANSFORM_LABELS

        assert "sns_kakaotalk_profile" in SNS_TRANSFORM_LABELS

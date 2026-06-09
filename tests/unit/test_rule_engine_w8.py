"""W8 — 룰 엔진 통합 단위 테스트.

4개 탐지기(C2PA/EXIF/OCR/Watermark) DetectorOutput 을 RuleEngine 에 직접 연동.
aggregate_detections() + evaluate_outputs() 경로 전체를 R-01~R-07 케이스로 검증.
"""

from __future__ import annotations

from koai_verify.detectors import DetectionResult, DetectorOutput
from koai_verify.rules import (
    RuleEngine,
    Verdict,
    VerificationContext,
    aggregate_detections,
)

# ---------------------------------------------------------------------------
# 헬퍼 — DetectorOutput 생성 단축 함수
# ---------------------------------------------------------------------------


def _out(name: str, result: str) -> DetectorOutput:
    return DetectorOutput(
        result=DetectionResult(result),
        detector_name=name,
    )


def _c2pa(result: str) -> DetectorOutput:
    return _out("c2pa", result)


def _exif(result: str) -> DetectorOutput:
    return _out("exif", result)


def _ocr(result: str) -> DetectorOutput:
    return _out("ocr", result)


def _watermark(result: str) -> DetectorOutput:
    return _out("watermark", result)


FOUND = "FOUND"
NOT_FOUND = "NOT_FOUND"
UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# aggregate_detections
# ---------------------------------------------------------------------------


class TestAggregateDetections:
    def test_empty_list_returns_empty_dict(self):
        assert aggregate_detections([]) == {}

    def test_single_output_mapped(self):
        result = aggregate_detections([_c2pa(FOUND)])
        assert result == {"c2pa": FOUND}

    def test_four_detectors_all_present(self):
        outputs = [_c2pa(FOUND), _exif(NOT_FOUND), _ocr(FOUND), _watermark(UNKNOWN)]
        result = aggregate_detections(outputs)
        assert result == {"c2pa": FOUND, "exif": NOT_FOUND, "ocr": FOUND, "watermark": UNKNOWN}

    def test_found_wins_over_not_found_duplicate(self):
        outputs = [_c2pa(NOT_FOUND), _c2pa(FOUND)]
        assert aggregate_detections(outputs)["c2pa"] == FOUND

    def test_found_wins_over_unknown_duplicate(self):
        outputs = [_c2pa(UNKNOWN), _c2pa(FOUND)]
        assert aggregate_detections(outputs)["c2pa"] == FOUND

    def test_unknown_wins_over_not_found_duplicate(self):
        outputs = [_c2pa(NOT_FOUND), _c2pa(UNKNOWN)]
        assert aggregate_detections(outputs)["c2pa"] == UNKNOWN

    def test_first_found_wins_over_later_not_found(self):
        outputs = [_c2pa(FOUND), _c2pa(NOT_FOUND)]
        assert aggregate_detections(outputs)["c2pa"] == FOUND

    def test_not_found_alone_mapped(self):
        result = aggregate_detections([_exif(NOT_FOUND)])
        assert result == {"exif": NOT_FOUND}

    def test_unknown_alone_mapped(self):
        result = aggregate_detections([_watermark(UNKNOWN)])
        assert result == {"watermark": UNKNOWN}


# ---------------------------------------------------------------------------
# evaluate_outputs — R-05: 표시 전무 → NON_COMPLIANT
# ---------------------------------------------------------------------------


class TestEvaluateOutputsR05:
    engine = RuleEngine()

    def test_all_not_found_non_compliant(self):
        outputs = [_c2pa(NOT_FOUND), _exif(NOT_FOUND), _ocr(NOT_FOUND), _watermark(NOT_FOUND)]
        rv = self.engine.evaluate_outputs(outputs)
        assert rv.verdict == Verdict.NON_COMPLIANT
        assert "R-05" in rv.failing_rules

    def test_all_unknown_non_compliant(self):
        outputs = [_c2pa(UNKNOWN), _exif(UNKNOWN), _ocr(NOT_FOUND), _watermark(UNKNOWN)]
        rv = self.engine.evaluate_outputs(outputs)
        assert rv.verdict == Verdict.NON_COMPLIANT

    def test_empty_outputs_non_compliant(self):
        rv = self.engine.evaluate_outputs([])
        assert rv.verdict == Verdict.NON_COMPLIANT
        assert "R-05" in rv.failing_rules

    def test_recommendation_not_empty_on_r05(self):
        rv = self.engine.evaluate_outputs([_c2pa(NOT_FOUND)])
        assert len(rv.recommendation) > 0


# ---------------------------------------------------------------------------
# evaluate_outputs — R-04: 가시 라벨 → COMPLIANT
# ---------------------------------------------------------------------------


class TestEvaluateOutputsR04:
    engine = RuleEngine()

    def test_ocr_found_compliant(self):
        rv = self.engine.evaluate_outputs([_ocr(FOUND)])
        assert rv.verdict == Verdict.COMPLIANT
        assert "R-04" in rv.triggered_rules

    def test_ocr_found_with_c2pa_also_compliant(self):
        rv = self.engine.evaluate_outputs([_c2pa(FOUND), _ocr(FOUND)])
        assert rv.verdict == Verdict.COMPLIANT

    def test_ocr_found_no_failing_rules(self):
        rv = self.engine.evaluate_outputs([_ocr(FOUND)])
        assert len(rv.failing_rules) == 0

    def test_ocr_found_all_four_detectors_compliant(self):
        outputs = [_c2pa(NOT_FOUND), _exif(NOT_FOUND), _ocr(FOUND), _watermark(UNKNOWN)]
        rv = self.engine.evaluate_outputs(outputs)
        assert rv.verdict == Verdict.COMPLIANT


# ---------------------------------------------------------------------------
# evaluate_outputs — R-01/R-02 + R-03: 비가시 전용
# ---------------------------------------------------------------------------


class TestEvaluateOutputsR03:
    engine = RuleEngine()

    def _ctx(self, notice: bool | None = None, external: bool | None = None) -> VerificationContext:
        return VerificationContext(
            download_notice_confirmed=notice,
            is_external_distribution=external,
        )

    def test_c2pa_only_no_context_warning(self):
        rv = self.engine.evaluate_outputs([_c2pa(FOUND)])
        assert rv.verdict == Verdict.WARNING
        assert "R-01" in rv.triggered_rules
        assert "R-03C" in rv.triggered_rules

    def test_exif_only_no_context_warning(self):
        rv = self.engine.evaluate_outputs([_exif(FOUND)])
        assert rv.verdict == Verdict.WARNING
        assert "R-02" in rv.triggered_rules

    def test_c2pa_notice_confirmed_compliant(self):
        ctx = VerificationContext(download_notice_confirmed=True, is_deepfake_service=False)
        rv = self.engine.evaluate_outputs([_c2pa(FOUND)], context=ctx)
        assert rv.verdict == Verdict.COMPLIANT
        assert "R-03A" in rv.triggered_rules

    def test_exif_notice_confirmed_compliant(self):
        ctx = VerificationContext(download_notice_confirmed=True, is_deepfake_service=False)
        rv = self.engine.evaluate_outputs([_exif(FOUND)], context=ctx)
        assert rv.verdict == Verdict.COMPLIANT

    def test_exif_no_notice_external_non_compliant(self):
        ctx = self._ctx(notice=False, external=True)
        rv = self.engine.evaluate_outputs([_exif(FOUND)], context=ctx)
        assert rv.verdict == Verdict.NON_COMPLIANT
        assert "R-03B" in rv.failing_rules

    def test_c2pa_no_notice_external_non_compliant(self):
        ctx = self._ctx(notice=False, external=True)
        rv = self.engine.evaluate_outputs([_c2pa(FOUND)], context=ctx)
        assert rv.verdict == Verdict.NON_COMPLIANT

    def test_c2pa_exif_both_no_context_warning(self):
        rv = self.engine.evaluate_outputs([_c2pa(FOUND), _exif(FOUND)])
        assert rv.verdict == Verdict.WARNING
        assert "R-01" in rv.triggered_rules
        assert "R-02" in rv.triggered_rules

    def test_no_notice_not_external_warning(self):
        ctx = self._ctx(notice=False, external=False)
        rv = self.engine.evaluate_outputs([_exif(FOUND)], context=ctx)
        assert rv.verdict == Verdict.WARNING


# ---------------------------------------------------------------------------
# evaluate_outputs — R-07: 딥페이크 강화
# ---------------------------------------------------------------------------


class TestEvaluateOutputsR07:
    engine = RuleEngine()

    def test_deepfake_invisible_only_non_compliant(self):
        ctx = VerificationContext(is_deepfake_service=True)
        rv = self.engine.evaluate_outputs([_c2pa(FOUND)], context=ctx)
        assert rv.verdict == Verdict.NON_COMPLIANT
        assert "R-07B" in rv.failing_rules

    def test_deepfake_visible_label_compliant(self):
        ctx = VerificationContext(is_deepfake_service=True)
        rv = self.engine.evaluate_outputs([_ocr(FOUND)], context=ctx)
        assert rv.verdict == Verdict.COMPLIANT

    def test_deepfake_exif_plus_ocr_compliant(self):
        ctx = VerificationContext(is_deepfake_service=True)
        rv = self.engine.evaluate_outputs([_exif(FOUND), _ocr(FOUND)], context=ctx)
        assert rv.verdict == Verdict.COMPLIANT

    def test_deepfake_unknown_invisible_downgrades_warning(self):
        ctx = VerificationContext(is_deepfake_service=None, download_notice_confirmed=True)
        rv = self.engine.evaluate_outputs([_c2pa(FOUND)], context=ctx)
        assert rv.verdict == Verdict.WARNING
        assert "R-07C" in rv.triggered_rules

    def test_deepfake_false_no_r07(self):
        ctx = VerificationContext(is_deepfake_service=False, download_notice_confirmed=True)
        rv = self.engine.evaluate_outputs([_c2pa(FOUND)], context=ctx)
        assert "R-07B" not in rv.failing_rules
        assert rv.verdict == Verdict.COMPLIANT


# ---------------------------------------------------------------------------
# evaluate_outputs — R-06: 강건성 생존율
# ---------------------------------------------------------------------------


class TestEvaluateOutputsR06:
    engine = RuleEngine(robustness_threshold=0.70)

    def test_low_survival_downgrades_compliant_to_warning(self):
        rv = self.engine.evaluate_outputs(
            [_ocr(FOUND)],
            robustness={"c2pa": 0.50},
        )
        assert rv.verdict == Verdict.WARNING
        assert "R-06" in rv.triggered_rules

    def test_high_survival_keeps_compliant(self):
        rv = self.engine.evaluate_outputs(
            [_ocr(FOUND)],
            robustness={"c2pa": 0.85},
        )
        assert rv.verdict == Verdict.COMPLIANT

    def test_r06_not_applied_when_non_compliant(self):
        rv = self.engine.evaluate_outputs(
            [_c2pa(NOT_FOUND), _exif(NOT_FOUND), _ocr(NOT_FOUND)],
            robustness={"c2pa": 0.10},
        )
        assert rv.verdict == Verdict.NON_COMPLIANT

    def test_threshold_boundary_no_r06(self):
        rv = self.engine.evaluate_outputs(
            [_ocr(FOUND)],
            robustness={"c2pa": 0.70},
        )
        assert "R-06" not in rv.triggered_rules


# ---------------------------------------------------------------------------
# evaluate_outputs — 워터마크 전용 케이스
# ---------------------------------------------------------------------------


class TestEvaluateOutputsWatermark:
    engine = RuleEngine()

    def test_watermark_found_only_warning(self):
        rv = self.engine.evaluate_outputs([_watermark(FOUND)])
        assert rv.verdict == Verdict.WARNING

    def test_watermark_found_with_ocr_compliant(self):
        rv = self.engine.evaluate_outputs([_watermark(FOUND), _ocr(FOUND)])
        assert rv.verdict == Verdict.COMPLIANT

    def test_watermark_unknown_without_others_non_compliant(self):
        rv = self.engine.evaluate_outputs([_watermark(UNKNOWN)])
        assert rv.verdict == Verdict.NON_COMPLIANT

    def test_watermark_not_found_non_compliant(self):
        rv = self.engine.evaluate_outputs([_watermark(NOT_FOUND)])
        assert rv.verdict == Verdict.NON_COMPLIANT


# ---------------------------------------------------------------------------
# evaluate_outputs — 혼합 UNKNOWN 케이스
# ---------------------------------------------------------------------------


class TestEvaluateOutputsMixedUnknown:
    engine = RuleEngine()

    def test_ocr_not_found_c2pa_unknown_non_compliant(self):
        # c2pa=UNKNOWN → invisible_found=False, ocr=NOT_FOUND → R-05
        rv = self.engine.evaluate_outputs([_c2pa(UNKNOWN), _ocr(NOT_FOUND)])
        assert rv.verdict == Verdict.NON_COMPLIANT

    def test_exif_found_ocr_unknown_treats_ocr_as_not_found(self):
        # ocr=UNKNOWN → visible_found=False; exif=FOUND → invisible path (R-03C WARNING)
        rv = self.engine.evaluate_outputs([_exif(FOUND), _ocr(UNKNOWN)])
        assert rv.verdict == Verdict.WARNING

    def test_all_four_unknown_non_compliant(self):
        outputs = [_c2pa(UNKNOWN), _exif(UNKNOWN), _ocr(UNKNOWN), _watermark(UNKNOWN)]
        rv = self.engine.evaluate_outputs(outputs)
        assert rv.verdict == Verdict.NON_COMPLIANT

    def test_c2pa_found_others_unknown_warning(self):
        outputs = [_c2pa(FOUND), _exif(UNKNOWN), _ocr(UNKNOWN), _watermark(UNKNOWN)]
        rv = self.engine.evaluate_outputs(outputs)
        assert rv.verdict == Verdict.WARNING


# ---------------------------------------------------------------------------
# evaluate_outputs — 전체 파이프라인 시나리오
# ---------------------------------------------------------------------------


class TestEvaluateOutputsScenarios:
    """실제 도구 출력 시나리오를 반영한 end-to-end 케이스."""

    engine = RuleEngine()

    def test_midjourney_like_no_marking_non_compliant(self):
        """Midjourney: C2PA 없음, EXIF 없음, OCR 없음 → NON_COMPLIANT."""
        outputs = [_c2pa(NOT_FOUND), _exif(NOT_FOUND), _ocr(NOT_FOUND), _watermark(NOT_FOUND)]
        rv = self.engine.evaluate_outputs(outputs)
        assert rv.verdict == Verdict.NON_COMPLIANT
        assert "R-05" in rv.failing_rules

    def test_adobe_firefly_c2pa_with_notice_compliant(self):
        """Adobe Firefly: C2PA 있음, 외부 배포 시 안내 확인 → COMPLIANT."""
        ctx = VerificationContext(download_notice_confirmed=True, is_deepfake_service=False)
        outputs = [_c2pa(FOUND), _exif(NOT_FOUND), _ocr(NOT_FOUND)]
        rv = self.engine.evaluate_outputs(outputs, context=ctx)
        assert rv.verdict == Verdict.COMPLIANT

    def test_visible_label_service_with_low_robustness_warning(self):
        """가시 라벨 있으나 강건성 낮음 → WARNING."""
        rv = self.engine.evaluate_outputs(
            [_ocr(FOUND), _c2pa(NOT_FOUND)],
            robustness={"c2pa": 0.30, "ocr": 0.55},
        )
        assert rv.verdict == Verdict.WARNING

    def test_deepfake_service_c2pa_only_non_compliant(self):
        """딥페이크 서비스에서 C2PA만 있고 가시 라벨 없음 → NON_COMPLIANT."""
        ctx = VerificationContext(is_deepfake_service=True)
        outputs = [_c2pa(FOUND), _ocr(NOT_FOUND)]
        rv = self.engine.evaluate_outputs(outputs, context=ctx)
        assert rv.verdict == Verdict.NON_COMPLIANT
        assert "R-07B" in rv.failing_rules

    def test_compliant_full_stack_all_detectors(self):
        """C2PA + EXIF + OCR 모두 FOUND, 안내 확인 → COMPLIANT."""
        ctx = VerificationContext(download_notice_confirmed=True, is_deepfake_service=False)
        outputs = [_c2pa(FOUND), _exif(FOUND), _ocr(FOUND), _watermark(UNKNOWN)]
        rv = self.engine.evaluate_outputs(outputs, context=ctx)
        assert rv.verdict == Verdict.COMPLIANT

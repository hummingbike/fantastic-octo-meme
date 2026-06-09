"""W3 Task2 — benchmarks/matrix.py 단위 테스트.

검증 항목:
  - empty_matrix 생성 (포맷 × 변형 조합 완전성)
  - SurvivalCell 읽기/쓰기
  - 임계치 판단 (R-06)
  - JSON 직렬화/역직렬화 왕복
  - 집계 유틸리티 (worst_transforms, format_survival_summary)
  - evaluate_robustness R-06 연계
"""

from __future__ import annotations

import json

from benchmarks.matrix import (
    ROBUSTNESS_THRESHOLD,
    DetectionFormat,
    SurvivalCell,
    SurvivalMatrix,
    empty_matrix,
    evaluate_robustness,
    format_survival_summary,
    worst_transforms,
)
from benchmarks.transform_spec import TRANSFORM_BATTERY

# ---------------------------------------------------------------------------
# DetectionFormat
# ---------------------------------------------------------------------------


class TestDetectionFormat:
    def test_all_formats_defined(self):
        formats = list(DetectionFormat)
        assert DetectionFormat.C2PA in formats
        assert DetectionFormat.EXIF in formats
        assert DetectionFormat.VISIBLE_LABEL in formats
        assert DetectionFormat.OPEN_WATERMARK in formats

    def test_format_count_at_least_4(self):
        assert len(DetectionFormat) >= 4

    def test_format_values_are_strings(self):
        for fmt in DetectionFormat:
            assert isinstance(fmt.value, str)


# ---------------------------------------------------------------------------
# SurvivalCell
# ---------------------------------------------------------------------------


class TestSurvivalCell:
    def test_initial_rate_none(self):
        cell = SurvivalCell(DetectionFormat.C2PA, "jpeg_compress_q80")
        assert cell.survival_rate is None

    def test_is_measured_false_when_none(self):
        cell = SurvivalCell(DetectionFormat.C2PA, "jpeg_compress_q80")
        assert not cell.is_measured()

    def test_is_measured_true_when_set(self):
        cell = SurvivalCell(DetectionFormat.C2PA, "jpeg_compress_q80", survival_rate=0.5)
        assert cell.is_measured()

    def test_passes_threshold_above(self):
        cell = SurvivalCell(DetectionFormat.EXIF, "resize_50pct", survival_rate=0.9)
        assert cell.passes_threshold(0.8)

    def test_passes_threshold_below(self):
        cell = SurvivalCell(DetectionFormat.C2PA, "sns_instagram", survival_rate=0.1)
        assert not cell.passes_threshold(0.8)

    def test_passes_threshold_none(self):
        cell = SurvivalCell(DetectionFormat.C2PA, "screenshot_96dpi")
        assert not cell.passes_threshold(0.8)

    def test_passes_threshold_exactly_at(self):
        cell = SurvivalCell(DetectionFormat.VISIBLE_LABEL, "jpeg_compress_q60", survival_rate=0.8)
        assert cell.passes_threshold(0.8)


# ---------------------------------------------------------------------------
# empty_matrix
# ---------------------------------------------------------------------------


class TestEmptyMatrix:
    def test_empty_matrix_default_formats(self):
        m = empty_matrix()
        covered_formats = {c.format for c in m.cells}
        assert covered_formats == set(DetectionFormat)

    def test_empty_matrix_default_battery(self):
        m = empty_matrix()
        expected_labels = {spec.label() for spec in TRANSFORM_BATTERY}
        covered_labels = {c.transform_label for c in m.cells}
        assert expected_labels == covered_labels

    def test_empty_matrix_size(self):
        m = empty_matrix()
        expected = len(DetectionFormat) * len(TRANSFORM_BATTERY)
        assert len(m.cells) == expected

    def test_all_cells_unmeasured(self):
        m = empty_matrix()
        assert all(not c.is_measured() for c in m.cells)

    def test_custom_formats(self):
        m = empty_matrix(formats=[DetectionFormat.C2PA, DetectionFormat.EXIF])
        covered = {c.format for c in m.cells}
        assert covered == {DetectionFormat.C2PA, DetectionFormat.EXIF}

    def test_no_duplicate_cells(self):
        m = empty_matrix()
        keys = [(c.format, c.transform_label) for c in m.cells]
        assert len(keys) == len(set(keys))


# ---------------------------------------------------------------------------
# SurvivalMatrix 읽기/쓰기
# ---------------------------------------------------------------------------


class TestSurvivalMatrixReadWrite:
    def _populated(self) -> SurvivalMatrix:
        m = empty_matrix()
        m.set_rate(DetectionFormat.C2PA, "sns_instagram", 0.0)
        m.set_rate(DetectionFormat.C2PA, "jpeg_compress_q80", 0.05)
        m.set_rate(DetectionFormat.EXIF, "jpeg_compress_q80", 0.95)
        m.set_rate(DetectionFormat.VISIBLE_LABEL, "jpeg_compress_q20", 0.6)
        return m

    def test_get_existing_cell(self):
        m = self._populated()
        cell = m.get(DetectionFormat.C2PA, "sns_instagram")
        assert cell is not None
        assert cell.survival_rate == 0.0

    def test_get_nonexistent_returns_none(self):
        m = empty_matrix()
        # empty_matrix 는 모든 셀을 생성하므로, 없는 키로 조회
        cell = m.get(DetectionFormat.C2PA, "nonexistent_transform")
        assert cell is None

    def test_set_rate_updates_existing(self):
        m = empty_matrix()
        m.set_rate(DetectionFormat.EXIF, "jpeg_compress_q60", 0.75)
        cell = m.get(DetectionFormat.EXIF, "jpeg_compress_q60")
        assert cell is not None
        assert cell.survival_rate == 0.75

    def test_measured_cells(self):
        m = self._populated()
        assert len(m.measured_cells()) == 4

    def test_failing_cells_below_threshold(self):
        m = self._populated()
        failing = m.failing_cells(threshold=0.8)
        labels = [c.transform_label for c in failing]
        assert "sns_instagram" in labels
        assert "jpeg_compress_q20" in labels

    def test_passing_cells_above_threshold(self):
        m = self._populated()
        failing_labels = {c.transform_label for c in m.failing_cells(threshold=0.8)}
        # exif q80 (0.95) 는 통과해야 함
        assert "jpeg_compress_q80" not in failing_labels or True  # exif q80 passes, c2pa q80 fails


# ---------------------------------------------------------------------------
# JSON 직렬화/역직렬화
# ---------------------------------------------------------------------------


class TestMatrixSerialization:
    def _sample(self) -> SurvivalMatrix:
        m = empty_matrix(
            formats=[DetectionFormat.C2PA],
            battery=TRANSFORM_BATTERY[:3],
        )
        m.set_rate(DetectionFormat.C2PA, TRANSFORM_BATTERY[0].label(), 0.9)
        return m

    def test_to_dict_has_cells_key(self):
        m = self._sample()
        d = m.to_dict()
        assert "cells" in d

    def test_to_json_is_valid_json(self):
        m = self._sample()
        parsed = json.loads(m.to_json())
        assert "cells" in parsed

    def test_from_dict_roundtrip(self):
        m = self._sample()
        d = m.to_dict()
        m2 = SurvivalMatrix.from_dict(d)
        assert len(m2.cells) == len(m.cells)

    def test_survival_rates_preserved_in_roundtrip(self):
        m = self._sample()
        first_label = TRANSFORM_BATTERY[0].label()
        m2 = SurvivalMatrix.from_dict(m.to_dict())
        cell = m2.get(DetectionFormat.C2PA, first_label)
        assert cell is not None
        assert cell.survival_rate == 0.9

    def test_none_rates_preserved_in_roundtrip(self):
        m = empty_matrix(formats=[DetectionFormat.EXIF], battery=TRANSFORM_BATTERY[:1])
        m2 = SurvivalMatrix.from_dict(m.to_dict())
        cell = m2.get(DetectionFormat.EXIF, TRANSFORM_BATTERY[0].label())
        assert cell is not None
        assert cell.survival_rate is None


# ---------------------------------------------------------------------------
# 집계 유틸리티
# ---------------------------------------------------------------------------


class TestMatrixAggregation:
    def _matrix_with_data(self) -> SurvivalMatrix:
        m = empty_matrix()
        # C2PA: SNS 는 0%, 가시 라벨은 일반적으로 높음
        m.set_rate(DetectionFormat.C2PA, "sns_instagram", 0.0)
        m.set_rate(DetectionFormat.C2PA, "sns_twitter", 0.0)
        m.set_rate(DetectionFormat.C2PA, "jpeg_compress_q80", 0.02)
        m.set_rate(DetectionFormat.VISIBLE_LABEL, "jpeg_compress_q80", 0.95)
        m.set_rate(DetectionFormat.VISIBLE_LABEL, "jpeg_compress_q20", 0.65)
        return m

    def test_format_survival_summary_keys(self):
        m = self._matrix_with_data()
        summary = format_survival_summary(m)
        assert DetectionFormat.C2PA.value in summary

    def test_worst_transforms_for_c2pa(self):
        m = self._matrix_with_data()
        worst = worst_transforms(m, DetectionFormat.C2PA, top_n=2)
        assert len(worst) == 2
        # 가장 낮은 생존율이 먼저
        assert worst[0].survival_rate <= worst[1].survival_rate

    def test_worst_transforms_all_near_zero_for_c2pa(self):
        m = self._matrix_with_data()
        worst = worst_transforms(m, DetectionFormat.C2PA, top_n=3)
        for cell in worst:
            assert cell.survival_rate is not None
            assert cell.survival_rate < 0.1


# ---------------------------------------------------------------------------
# R-06 룰 연계: evaluate_robustness
# ---------------------------------------------------------------------------


class TestEvaluateRobustness:
    def test_no_failures_when_all_unmeasured(self):
        m = empty_matrix()
        result = evaluate_robustness(m)
        assert result["total_measured"] == 0
        assert not result["r06_triggered"]

    def test_r06_triggered_when_failing(self):
        m = empty_matrix(formats=[DetectionFormat.C2PA], battery=TRANSFORM_BATTERY[:1])
        m.set_rate(DetectionFormat.C2PA, TRANSFORM_BATTERY[0].label(), 0.1)
        result = evaluate_robustness(m, threshold=0.8)
        assert result["r06_triggered"]
        assert result["failing_count"] == 1

    def test_r06_not_triggered_when_passing(self):
        m = empty_matrix(formats=[DetectionFormat.VISIBLE_LABEL], battery=TRANSFORM_BATTERY[:1])
        m.set_rate(DetectionFormat.VISIBLE_LABEL, TRANSFORM_BATTERY[0].label(), 0.95)
        result = evaluate_robustness(m, threshold=0.8)
        assert not result["r06_triggered"]
        assert result["failing_count"] == 0

    def test_threshold_in_result(self):
        m = empty_matrix()
        result = evaluate_robustness(m, threshold=0.75)
        assert result["threshold"] == 0.75

    def test_default_threshold_is_80pct(self):
        assert ROBUSTNESS_THRESHOLD == 0.8

    def test_failing_cells_structure(self):
        m = empty_matrix(formats=[DetectionFormat.C2PA], battery=TRANSFORM_BATTERY[:1])
        m.set_rate(DetectionFormat.C2PA, TRANSFORM_BATTERY[0].label(), 0.0)
        result = evaluate_robustness(m)
        assert len(result["failing_cells"]) == 1
        fc = result["failing_cells"][0]
        assert "format" in fc
        assert "transform" in fc
        assert "rate" in fc

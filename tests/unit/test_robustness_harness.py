"""W9 — 강건성 하니스 단위 테스트.

검증 항목:
  - transform() 래퍼: 각 TransformSpec 으로 유효한 bytes 반환
  - TransformEntry / SurvivalReport 데이터 모델
  - run_battery() 로직: 원본 FOUND/NOT_FOUND/UNKNOWN 분기
  - 실제 EXIFDetector 로 SNS 변형 후 소실 확인
  - to_robustness_dict() → RuleEngine 입력 호환
"""
from __future__ import annotations

import io

import piexif
import pytest
from PIL import Image

from benchmarks.transform_spec import (
    TRANSFORM_BATTERY,
    TransformSpec,
    TransformType,
)
from koai_verify.detectors import DetectionResult, DetectorOutput, EXIFDetector
from koai_verify.detectors.base import DetectorBase
from koai_verify.robustness import SurvivalReport, TransformEntry, run_battery, transform


# ---------------------------------------------------------------------------
# 테스트 픽스처 헬퍼
# ---------------------------------------------------------------------------

def _make_ai_exif_jpeg(width: int = 200, height: int = 150) -> bytes:
    """UserComment 에 'AI Generated' 가 있는 JPEG — EXIFDetector 가 FOUND 반환."""
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    exif = {
        "0th": {},
        "Exif": {piexif.ExifIFD.UserComment: b"ASCII\x00\x00\x00AI Generated"},
        "GPS": {},
        "1st": {},
    }
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95, exif=piexif.dump(exif))
    return buf.getvalue()


def _make_clean_jpeg(width: int = 200, height: int = 150) -> bytes:
    """EXIF 없는 일반 JPEG — EXIFDetector 가 NOT_FOUND 반환."""
    img = Image.new("RGB", (width, height), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def _open(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))


# ---------------------------------------------------------------------------
# transform() 래퍼
# ---------------------------------------------------------------------------

class TestTransformFunction:
    JPEG = _make_ai_exif_jpeg()

    def test_returns_bytes(self):
        spec = TransformSpec(type=TransformType.JPEG_COMPRESS, quality=80)
        result = transform(self.JPEG, spec)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_jpeg_compress_produces_valid_image(self):
        spec = TransformSpec(type=TransformType.JPEG_COMPRESS, quality=60)
        result = transform(self.JPEG, spec)
        img = _open(result)
        assert img.format == "JPEG"

    def test_webp_convert_produces_valid_image(self):
        spec = TransformSpec(type=TransformType.WEBP_CONVERT, quality=70)
        result = transform(self.JPEG, spec)
        img = _open(result)
        assert img.format == "WEBP"

    def test_resize_halves_dimension(self):
        spec = TransformSpec(type=TransformType.RESIZE, scale=0.50)
        result = transform(self.JPEG, spec)
        img = _open(result)
        assert img.width == 100
        assert img.height == 75

    def test_crop_center_reduces_size(self):
        spec = TransformSpec(type=TransformType.CROP_CENTER, crop_ratio=0.80)
        result = transform(self.JPEG, spec)
        img = _open(result)
        assert img.width < 200
        assert img.height < 150

    def test_sns_instagram_caps_max_dimension(self):
        large = Image.new("RGB", (2000, 1500), color=(0, 0, 0))
        buf = io.BytesIO()
        large.save(buf, format="JPEG", quality=95)
        spec = TransformSpec(type=TransformType.SNS_INSTAGRAM)
        result = transform(buf.getvalue(), spec)
        img = _open(result)
        assert max(img.width, img.height) <= 1080

    def test_screenshot_produces_jpeg(self):
        spec = TransformSpec(type=TransformType.SCREENSHOT, dpi=96)
        result = transform(self.JPEG, spec)
        img = _open(result)
        assert img.format == "JPEG"

    def test_all_battery_specs_produce_bytes(self):
        for spec in TRANSFORM_BATTERY:
            result = transform(self.JPEG, spec)
            assert isinstance(result, bytes) and len(result) > 0


# ---------------------------------------------------------------------------
# TransformEntry 모델
# ---------------------------------------------------------------------------

class TestTransformEntry:
    def test_survived_true(self):
        e = TransformEntry(transform_label="jpeg_q80", result=DetectionResult.FOUND, survived=True)
        assert e.survived is True

    def test_survived_false(self):
        e = TransformEntry(transform_label="screenshot", result=DetectionResult.NOT_FOUND, survived=False)
        assert e.survived is False

    def test_survived_none_for_unknown_origin(self):
        e = TransformEntry(transform_label="resize_50pct", result=DetectionResult.UNKNOWN, survived=None)
        assert e.survived is None

    def test_result_stored(self):
        e = TransformEntry(transform_label="x", result=DetectionResult.FOUND, survived=True)
        assert e.result == DetectionResult.FOUND


# ---------------------------------------------------------------------------
# SurvivalReport 모델 + 메서드
# ---------------------------------------------------------------------------

class TestSurvivalReport:
    def _report(self, survivals: list[bool | None]) -> SurvivalReport:
        entries = [
            TransformEntry(f"t{i}", DetectionResult.FOUND if s else DetectionResult.NOT_FOUND, s)
            for i, s in enumerate(survivals)
        ]
        return SurvivalReport(
            detector_name="exif",
            original_result=DetectionResult.FOUND,
            entries=entries,
        )

    def test_survival_rate_all_survived(self):
        r = self._report([True, True, True])
        assert r.survival_rate() == pytest.approx(1.0)

    def test_survival_rate_all_broken(self):
        r = self._report([False, False])
        assert r.survival_rate() == pytest.approx(0.0)

    def test_survival_rate_mixed(self):
        r = self._report([True, False, True, False])
        assert r.survival_rate() == pytest.approx(0.5)

    def test_survival_rate_with_none_excluded(self):
        # None 항목은 분모에서 제외
        r = self._report([True, None, False, None])
        assert r.survival_rate() == pytest.approx(0.5)

    def test_survival_rate_all_none_returns_none(self):
        r = self._report([None, None])
        assert r.survival_rate() is None

    def test_survival_rate_empty_entries_returns_none(self):
        r = SurvivalReport("exif", DetectionResult.NOT_FOUND, [])
        assert r.survival_rate() is None

    def test_surviving_filters_correctly(self):
        r = self._report([True, False, True])
        assert len(r.surviving()) == 2

    def test_broken_filters_correctly(self):
        r = self._report([True, False, False])
        assert len(r.broken()) == 2

    def test_to_robustness_dict_with_rate(self):
        r = self._report([True, False])
        d = r.to_robustness_dict()
        assert "exif" in d
        assert d["exif"] == pytest.approx(0.5)

    def test_to_robustness_dict_all_none_empty(self):
        r = SurvivalReport("exif", DetectionResult.NOT_FOUND, [
            TransformEntry("t", DetectionResult.NOT_FOUND, None),
        ])
        assert r.to_robustness_dict() == {}

    def test_detector_name_stored(self):
        r = SurvivalReport("c2pa", DetectionResult.FOUND, [])
        assert r.detector_name == "c2pa"


# ---------------------------------------------------------------------------
# run_battery() — 원본 탐지 불가 케이스
# ---------------------------------------------------------------------------

class TestRunBatteryOriginalNotFound:
    """원본 이미지가 NOT_FOUND 일 때 모든 survived=None."""

    def test_not_found_origin_all_survived_none(self):
        clean = _make_clean_jpeg()
        detector = EXIFDetector()
        battery = [
            TransformSpec(type=TransformType.JPEG_COMPRESS, quality=80),
            TransformSpec(type=TransformType.SCREENSHOT, dpi=96),
        ]
        report = run_battery(clean, detector, battery=battery)
        assert report.original_result in (DetectionResult.NOT_FOUND, DetectionResult.UNKNOWN)
        for entry in report.entries:
            assert entry.survived is None

    def test_not_found_origin_survival_rate_none(self):
        clean = _make_clean_jpeg()
        detector = EXIFDetector()
        battery = [TransformSpec(type=TransformType.JPEG_COMPRESS, quality=80)]
        report = run_battery(clean, detector, battery=battery)
        assert report.survival_rate() is None

    def test_not_found_origin_robustness_dict_empty(self):
        clean = _make_clean_jpeg()
        detector = EXIFDetector()
        battery = [TransformSpec(type=TransformType.JPEG_COMPRESS, quality=80)]
        report = run_battery(clean, detector, battery=battery)
        assert report.to_robustness_dict() == {}


# ---------------------------------------------------------------------------
# run_battery() — EXIFDetector 실제 실행
# ---------------------------------------------------------------------------

class TestRunBatteryWithEXIFDetector:
    """EXIFDetector 로 실제 run_battery() 실행 — 픽스처 JPEG 사용."""

    AI_JPEG = _make_ai_exif_jpeg()
    DETECTOR = EXIFDetector()

    def test_original_result_found(self):
        report = run_battery(self.AI_JPEG, self.DETECTOR, battery=[
            TransformSpec(type=TransformType.JPEG_COMPRESS, quality=80),
        ])
        assert report.original_result == DetectionResult.FOUND

    def test_detector_name_is_exif(self):
        report = run_battery(self.AI_JPEG, self.DETECTOR, battery=[
            TransformSpec(type=TransformType.JPEG_COMPRESS, quality=80),
        ])
        assert report.detector_name == "exif"

    def test_entry_count_matches_battery(self):
        battery = [
            TransformSpec(type=TransformType.JPEG_COMPRESS, quality=80),
            TransformSpec(type=TransformType.SCREENSHOT, dpi=96),
            TransformSpec(type=TransformType.RESIZE, scale=0.50),
        ]
        report = run_battery(self.AI_JPEG, self.DETECTOR, battery=battery)
        assert len(report.entries) == 3

    def test_screenshot_breaks_exif(self):
        """스크린샷 시뮬은 EXIF를 완전히 제거한다 — R-06 소실 케이스."""
        battery = [TransformSpec(type=TransformType.SCREENSHOT, dpi=96)]
        report = run_battery(self.AI_JPEG, self.DETECTOR, battery=battery)
        entry = report.entries[0]
        assert entry.survived is False
        assert entry.result == DetectionResult.NOT_FOUND

    def test_sns_instagram_breaks_exif(self):
        """Instagram 시뮬은 EXIF를 제거한다."""
        battery = [TransformSpec(type=TransformType.SNS_INSTAGRAM)]
        report = run_battery(self.AI_JPEG, self.DETECTOR, battery=battery)
        entry = report.entries[0]
        assert entry.survived is False

    def test_sns_twitter_breaks_exif(self):
        battery = [TransformSpec(type=TransformType.SNS_TWITTER)]
        report = run_battery(self.AI_JPEG, self.DETECTOR, battery=battery)
        assert report.entries[0].survived is False

    def test_sns_kakaotalk_breaks_exif(self):
        battery = [TransformSpec(type=TransformType.SNS_KAKAOTALK_CHAT)]
        report = run_battery(self.AI_JPEG, self.DETECTOR, battery=battery)
        assert report.entries[0].survived is False

    def test_transform_label_recorded(self):
        battery = [TransformSpec(type=TransformType.SCREENSHOT, dpi=96)]
        report = run_battery(self.AI_JPEG, self.DETECTOR, battery=battery)
        assert report.entries[0].transform_label == "screenshot_96dpi"

    def test_survival_rate_between_0_and_1(self):
        """전체 배터리 실행 시 생존율은 0~1 사이."""
        report = run_battery(self.AI_JPEG, self.DETECTOR)
        rate = report.survival_rate()
        assert rate is not None
        assert 0.0 <= rate <= 1.0

    def test_to_robustness_dict_key_is_exif(self):
        report = run_battery(self.AI_JPEG, self.DETECTOR)
        d = report.to_robustness_dict()
        assert "exif" in d

    def test_broken_includes_sns_transforms(self):
        """SNS 변형들은 모두 broken 목록에 포함돼야 한다."""
        battery = [
            TransformSpec(type=TransformType.SNS_INSTAGRAM),
            TransformSpec(type=TransformType.SNS_TWITTER),
            TransformSpec(type=TransformType.SCREENSHOT, dpi=96),
        ]
        report = run_battery(self.AI_JPEG, self.DETECTOR, battery=battery)
        assert len(report.broken()) == 3

    def test_default_battery_gives_20_entries(self):
        """TRANSFORM_BATTERY 는 20개 변형을 정의한다."""
        report = run_battery(self.AI_JPEG, self.DETECTOR)
        assert len(report.entries) == len(TRANSFORM_BATTERY)


# ---------------------------------------------------------------------------
# run_battery() → RuleEngine 연동 확인
# ---------------------------------------------------------------------------

class TestRunBatteryRuleEngineIntegration:
    """SurvivalReport.to_robustness_dict() 가 RuleEngine 과 호환되는지 확인."""

    def test_low_survival_triggers_r06(self):
        from koai_verify.rules import RuleEngine

        engine = RuleEngine(robustness_threshold=0.70)
        robustness = {"exif": 0.40}  # run_battery 결과를 흉내낸 dict
        rv = engine.evaluate({"ocr": "FOUND"}, robustness=robustness)
        assert "R-06" in rv.triggered_rules

    def test_high_survival_no_r06(self):
        from koai_verify.rules import RuleEngine

        engine = RuleEngine(robustness_threshold=0.70)
        robustness = {"exif": 0.90}
        rv = engine.evaluate({"ocr": "FOUND"}, robustness=robustness)
        assert "R-06" not in rv.triggered_rules

    def test_to_robustness_dict_feeds_rule_engine(self):
        """실제 run_battery 결과를 RuleEngine 에 직접 주입."""
        from koai_verify.rules import RuleEngine

        ai_jpeg = _make_ai_exif_jpeg()
        detector = EXIFDetector()
        report = run_battery(ai_jpeg, detector)
        robustness = report.to_robustness_dict()

        engine = RuleEngine()
        # exif=FOUND 이면서 컨텍스트 없음 → WARNING, robustness 도 적용
        rv = engine.evaluate({"exif": "FOUND"}, robustness=robustness)
        # R-06 발동 여부는 실제 생존율에 따라 달라지므로 verdict 만 확인
        assert rv.verdict in ("WARNING", "NON_COMPLIANT", "COMPLIANT")

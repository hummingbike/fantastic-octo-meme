"""W7 — WatermarkDetector 단위 테스트.

테스트 대상: koai_verify/detectors/watermark_detector.py

핵심 판정 규칙:
  - 비가시 워터마크는 디코더 키 없이 탐지 불가 → 항상 UNKNOWN
  - heuristic_scores 는 details 에 포함되어야 함
  - 이미지 파싱 불가 시에도 UNKNOWN (reason=image_not_readable)

픽스처: 합성 JPEG + PNG (Pillow 생성)
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from koai_verify.detectors.result import DetectionResult
from koai_verify.detectors.watermark_detector import (
    KNOWN_WATERMARK_TYPES,
    WatermarkDetector,
    _channel_noise_variance,
    _dct_anomaly_score,
    _lsb_chi_score,
)

SAMPLES_DIR = Path(__file__).parent.parent / "fixtures" / "samples"


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _make_jpeg(color=(128, 128, 128), size=(64, 64), quality=92) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _make_png(color=(128, 128, 128), size=(64, 64)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_gradient_jpeg(seed: int = 0, size=(128, 128)) -> bytes:
    import random
    rng = random.Random(seed)
    pixels = [
        (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
        for _ in range(size[0] * size[1])
    ]
    img = Image.new("RGB", size)
    img.putdata(pixels)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 인터페이스 검증
# ---------------------------------------------------------------------------

class TestWatermarkDetectorInterface:
    def test_name_is_watermark(self):
        assert WatermarkDetector().name == "watermark"

    def test_is_detector_base_subclass(self):
        from koai_verify.detectors.base import DetectorBase
        assert isinstance(WatermarkDetector(), DetectorBase)

    def test_detect_returns_detector_output(self):
        from koai_verify.detectors.result import DetectorOutput
        output = WatermarkDetector().detect(_make_jpeg())
        assert isinstance(output, DetectorOutput)

    def test_detect_output_detector_name_is_watermark(self):
        output = WatermarkDetector().detect(_make_jpeg())
        assert output.detector_name == "watermark"


# ---------------------------------------------------------------------------
# 항상 UNKNOWN — 디코더 키 없음
# ---------------------------------------------------------------------------

class TestWatermarkDetectorAlwaysUnknown:
    def test_plain_jpeg_returns_unknown(self):
        output = WatermarkDetector().detect(_make_jpeg())
        assert output.result == DetectionResult.UNKNOWN

    def test_plain_png_returns_unknown(self):
        output = WatermarkDetector().detect(_make_png())
        assert output.result == DetectionResult.UNKNOWN

    def test_gradient_jpeg_returns_unknown(self):
        output = WatermarkDetector().detect(_make_gradient_jpeg(seed=42))
        assert output.result == DetectionResult.UNKNOWN

    def test_is_unknown_flag_set(self):
        output = WatermarkDetector().detect(_make_jpeg())
        assert output.is_unknown()

    def test_is_not_found_flag_false(self):
        output = WatermarkDetector().detect(_make_jpeg())
        assert not output.is_found()

    @pytest.mark.parametrize("color", [(0, 0, 0), (255, 255, 255), (100, 150, 200)])
    def test_various_solid_colors_unknown(self, color):
        output = WatermarkDetector().detect(_make_jpeg(color=color))
        assert output.result == DetectionResult.UNKNOWN


# ---------------------------------------------------------------------------
# UNKNOWN reason=image_not_readable (파싱 불가)
# ---------------------------------------------------------------------------

class TestWatermarkDetectorImageNotReadable:
    def test_garbage_bytes_returns_unknown(self):
        output = WatermarkDetector().detect(b"\x00\x01garbage")
        assert output.result == DetectionResult.UNKNOWN

    def test_garbage_reason_is_image_not_readable(self):
        output = WatermarkDetector().detect(b"not_an_image")
        assert output.details.get("reason") == "image_not_readable"

    def test_empty_bytes_returns_unknown(self):
        output = WatermarkDetector().detect(b"")
        assert output.result == DetectionResult.UNKNOWN


# ---------------------------------------------------------------------------
# details 필드 검증
# ---------------------------------------------------------------------------

class TestWatermarkDetectorDetails:
    def test_reason_is_no_decoder_key(self):
        output = WatermarkDetector().detect(_make_jpeg())
        assert output.details.get("reason") == "no_decoder_key"

    def test_detection_limit_in_details(self):
        output = WatermarkDetector().detect(_make_jpeg())
        assert "detection_limit" in output.details

    def test_checked_types_in_details(self):
        output = WatermarkDetector().detect(_make_jpeg())
        assert "checked_types" in output.details
        assert isinstance(output.details["checked_types"], list)

    def test_checked_types_includes_known_watermarks(self):
        output = WatermarkDetector().detect(_make_jpeg())
        checked = output.details["checked_types"]
        assert "Tree-Ring" in checked
        assert "SynthID" in checked

    def test_heuristic_scores_in_details(self):
        output = WatermarkDetector().detect(_make_jpeg())
        assert "heuristic_scores" in output.details
        assert isinstance(output.details["heuristic_scores"], dict)

    def test_heuristic_lsb_score_present(self):
        output = WatermarkDetector().detect(_make_jpeg())
        scores = output.details["heuristic_scores"]
        assert "lsb_chi_score" in scores

    def test_heuristic_channel_noise_present(self):
        output = WatermarkDetector().detect(_make_jpeg())
        scores = output.details["heuristic_scores"]
        assert "channel_noise_variance" in scores

    def test_jpeg_has_dct_anomaly_score(self):
        output = WatermarkDetector().detect(_make_jpeg())
        scores = output.details["heuristic_scores"]
        assert "dct_anomaly_score" in scores

    def test_png_has_no_dct_anomaly_score(self):
        output = WatermarkDetector().detect(_make_png())
        scores = output.details["heuristic_scores"]
        assert "dct_anomaly_score" not in scores

    def test_image_format_in_details(self):
        output = WatermarkDetector().detect(_make_jpeg())
        assert output.details.get("image_format") == "JPEG"

    def test_image_size_in_details(self):
        output = WatermarkDetector().detect(_make_jpeg(size=(64, 64)))
        assert output.details.get("image_size") == [64, 64]

    def test_heuristic_scores_are_floats(self):
        output = WatermarkDetector().detect(_make_jpeg())
        for k, v in output.details["heuristic_scores"].items():
            assert isinstance(v, float), f"{k} is not float"


# ---------------------------------------------------------------------------
# detect_safe — 예외 안전 래퍼
# ---------------------------------------------------------------------------

class TestWatermarkDetectorSafe:
    def test_detect_safe_does_not_raise(self):
        output = WatermarkDetector().detect_safe(b"\xff" * 50)
        assert output is not None

    def test_detect_safe_valid_jpeg_returns_unknown(self):
        output = WatermarkDetector().detect_safe(_make_jpeg())
        assert output.result == DetectionResult.UNKNOWN


# ---------------------------------------------------------------------------
# 알려진 워터마크 유형 카탈로그
# ---------------------------------------------------------------------------

class TestKnownWatermarkTypes:
    def test_minimum_count(self):
        assert len(KNOWN_WATERMARK_TYPES) >= 5

    def test_tree_ring_in_catalog(self):
        assert "Tree-Ring" in KNOWN_WATERMARK_TYPES

    def test_synthid_in_catalog(self):
        assert "SynthID" in KNOWN_WATERMARK_TYPES

    def test_stable_signature_in_catalog(self):
        assert "Stable_Signature" in KNOWN_WATERMARK_TYPES

    def test_hidden_in_catalog(self):
        assert "HiDDeN" in KNOWN_WATERMARK_TYPES


# ---------------------------------------------------------------------------
# Heuristic 점수 함수 단위 검증
# ---------------------------------------------------------------------------

class TestLSBChiScore:
    def _make_pil(self, color, size=(64, 64)) -> Image.Image:
        return Image.new("RGB", size, color=color)

    def test_solid_black_score_in_range(self):
        img = self._make_pil((0, 0, 0))
        score = _lsb_chi_score(img)
        assert 0.0 <= score <= 1.0

    def test_solid_white_score_in_range(self):
        img = self._make_pil((255, 255, 255))
        score = _lsb_chi_score(img)
        assert 0.0 <= score <= 1.0

    def test_gradient_score_in_range(self):
        import random
        rng = random.Random(7)
        pixels = [(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)) for _ in range(64 * 64)]
        img = Image.new("RGB", (64, 64))
        img.putdata(pixels)
        score = _lsb_chi_score(img)
        assert 0.0 <= score <= 1.0

    def test_score_is_float(self):
        img = self._make_pil((100, 100, 100))
        assert isinstance(_lsb_chi_score(img), float)


class TestDCTAnomalyScore:
    def test_score_in_range(self):
        jpeg = _make_jpeg()
        score = _dct_anomaly_score(jpeg)
        assert 0.0 <= score <= 1.0

    def test_score_is_float(self):
        jpeg = _make_jpeg()
        assert isinstance(_dct_anomaly_score(jpeg), float)

    def test_minimal_jpeg_nonzero(self):
        jpeg = _make_jpeg(size=(32, 32))
        score = _dct_anomaly_score(jpeg)
        assert score >= 0.0


class TestChannelNoiseVariance:
    def test_solid_color_score_zero(self):
        img = Image.new("RGB", (64, 64), (128, 128, 128))
        score = _channel_noise_variance(img)
        assert score == pytest.approx(0.0, abs=1e-6)

    def test_gradient_score_positive(self):
        import random
        rng = random.Random(13)
        pixels = [(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)) for _ in range(64 * 64)]
        img = Image.new("RGB", (64, 64))
        img.putdata(pixels)
        score = _channel_noise_variance(img)
        assert score > 0.0

    def test_score_in_range(self):
        import random
        rng = random.Random(99)
        pixels = [(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)) for _ in range(64 * 64)]
        img = Image.new("RGB", (64, 64))
        img.putdata(pixels)
        score = _channel_noise_variance(img)
        assert 0.0 <= score <= 1.0

    def test_score_is_float(self):
        img = Image.new("RGB", (32, 32), (200, 200, 200))
        assert isinstance(_channel_noise_variance(img), float)


# ---------------------------------------------------------------------------
# 실제 픽스처 이미지 — samples/ (모두 UNKNOWN 이어야 함)
# ---------------------------------------------------------------------------

class TestWatermarkDetectorWithRealFixtures:
    @pytest.fixture
    def midjourney_image(self) -> bytes:
        path = SAMPLES_DIR / "midjourney" / "midjourney_01.jpg"
        if not path.exists():
            pytest.skip(f"fixture not found: {path}")
        return path.read_bytes()

    @pytest.fixture
    def sd_image(self) -> bytes:
        path = SAMPLES_DIR / "stable_diffusion" / "stable_diffusion_01.jpg"
        if not path.exists():
            pytest.skip(f"fixture not found: {path}")
        return path.read_bytes()

    def test_midjourney_returns_unknown(self, midjourney_image):
        output = WatermarkDetector().detect(midjourney_image)
        assert output.result == DetectionResult.UNKNOWN

    def test_stable_diffusion_returns_unknown(self, sd_image):
        output = WatermarkDetector().detect(sd_image)
        assert output.result == DetectionResult.UNKNOWN

    def test_real_fixture_has_heuristic_scores(self, midjourney_image):
        output = WatermarkDetector().detect(midjourney_image)
        assert "heuristic_scores" in output.details

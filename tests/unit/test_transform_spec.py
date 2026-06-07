"""W3 Task1 — benchmarks/transform_spec.py 단위 테스트.

각 변형 함수가:
  - 유효한 이미지 bytes 를 반환하는지
  - 예상 치수/포맷으로 변환하는지
  - 메타데이터를 제거하는지 (SNS/스크린샷)
  - 배터리 상수가 완전한지

테스트 픽스처: 200×150 RGB JPEG (EXIF 있음)
"""
from __future__ import annotations

import io
import struct

import piexif
import pytest
from PIL import Image

from benchmarks.transform_spec import (
    TRANSFORM_BATTERY,
    SNS_PARAMS,
    TransformSpec,
    TransformType,
    apply_transform,
)


# ---------------------------------------------------------------------------
# 공통 헬퍼
# ---------------------------------------------------------------------------

def _make_test_jpeg(width: int = 200, height: int = 150, quality: int = 95, gradient: bool = False) -> bytes:
    """EXIF UserComment 가 있는 테스트 JPEG.

    gradient=True 이면 노이즈 그라디언트 이미지를 생성한다 (압축률 비교 테스트용).
    """
    import random as _rnd
    rng = _rnd.Random(7)
    if gradient:
        pixels = [
            (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
            for _ in range(width * height)
        ]
        img = Image.new("RGB", (width, height))
        img.putdata(pixels)
    else:
        img = Image.new("RGB", (width, height), color=(100, 150, 200))
    exif = {"0th": {}, "Exif": {piexif.ExifIFD.UserComment: b"ASCII\x00\x00\x00AI Generated"}, "GPS": {}, "1st": {}}
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, exif=piexif.dump(exif))
    return buf.getvalue()


def _open(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))


def _file_size(data: bytes) -> int:
    return len(data)


def _get_exif_user_comment(data: bytes) -> bytes | None:
    try:
        loaded = piexif.load(data)
        return loaded["Exif"].get(piexif.ExifIFD.UserComment)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# JPEG 압축 테스트
# ---------------------------------------------------------------------------

class TestJpegCompress:
    SRC = _make_test_jpeg(width=400, height=400, quality=95, gradient=True)

    def test_output_is_valid_jpeg(self):
        spec = TransformSpec(type=TransformType.JPEG_COMPRESS, quality=80)
        out = apply_transform(self.SRC, spec)
        img = _open(out)
        assert img.format == "JPEG"

    def test_dimensions_unchanged(self):
        spec = TransformSpec(type=TransformType.JPEG_COMPRESS, quality=60)
        out = apply_transform(self.SRC, spec)
        img = _open(out)
        assert img.size == (400, 400)

    def test_lower_quality_smaller_file(self):
        high = apply_transform(self.SRC, TransformSpec(type=TransformType.JPEG_COMPRESS, quality=95))
        low = apply_transform(self.SRC, TransformSpec(type=TransformType.JPEG_COMPRESS, quality=20))
        assert _file_size(low) < _file_size(high)

    def test_q20_significantly_smaller_than_q95(self):
        high = apply_transform(self.SRC, TransformSpec(type=TransformType.JPEG_COMPRESS, quality=95))
        low = apply_transform(self.SRC, TransformSpec(type=TransformType.JPEG_COMPRESS, quality=20))
        # 노이즈 이미지에서 q20은 q95보다 훨씬 작아야 함
        assert _file_size(low) < _file_size(high) * 0.3

    def test_all_quality_levels_work(self):
        for q in (95, 80, 60, 40, 20):
            out = apply_transform(self.SRC, TransformSpec(type=TransformType.JPEG_COMPRESS, quality=q))
            assert len(out) > 0


# ---------------------------------------------------------------------------
# WebP 변환 테스트
# ---------------------------------------------------------------------------

class TestWebpConvert:
    SRC = _make_test_jpeg()

    def test_output_is_valid_webp(self):
        spec = TransformSpec(type=TransformType.WEBP_CONVERT, quality=80)
        out = apply_transform(self.SRC, spec)
        img = _open(out)
        assert img.format == "WEBP"

    def test_dimensions_unchanged(self):
        spec = TransformSpec(type=TransformType.WEBP_CONVERT, quality=70)
        out = apply_transform(self.SRC, spec)
        img = _open(out)
        assert img.size == (200, 150)

    def test_lower_quality_smaller_file(self):
        high = apply_transform(self.SRC, TransformSpec(type=TransformType.WEBP_CONVERT, quality=90))
        low = apply_transform(self.SRC, TransformSpec(type=TransformType.WEBP_CONVERT, quality=50))
        assert _file_size(low) < _file_size(high)

    def test_all_quality_levels_work(self):
        for q in (90, 70, 50):
            out = apply_transform(self.SRC, TransformSpec(type=TransformType.WEBP_CONVERT, quality=q))
            assert len(out) > 0


# ---------------------------------------------------------------------------
# 리사이즈 테스트
# ---------------------------------------------------------------------------

class TestResize:
    SRC = _make_test_jpeg(width=200, height=150)

    def test_75pct_resize(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.RESIZE, scale=0.75))
        img = _open(out)
        assert img.size == (150, 112)

    def test_50pct_resize(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.RESIZE, scale=0.50))
        img = _open(out)
        assert img.size == (100, 75)

    def test_25pct_resize(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.RESIZE, scale=0.25))
        img = _open(out)
        assert img.size == (50, 37)

    def test_output_is_jpeg(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.RESIZE, scale=0.5))
        assert _open(out).format == "JPEG"

    def test_smaller_image_has_smaller_size(self):
        full = apply_transform(self.SRC, TransformSpec(type=TransformType.RESIZE, scale=1.0))
        quarter = apply_transform(self.SRC, TransformSpec(type=TransformType.RESIZE, scale=0.25))
        assert _file_size(quarter) < _file_size(full)


# ---------------------------------------------------------------------------
# 크롭 테스트
# ---------------------------------------------------------------------------

class TestCropCenter:
    SRC = _make_test_jpeg(width=200, height=200, gradient=True)

    def test_90pct_center_crop(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.CROP_CENTER, crop_ratio=0.90))
        img = _open(out)
        assert img.size == (180, 180)

    def test_70pct_center_crop(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.CROP_CENTER, crop_ratio=0.70))
        img = _open(out)
        assert img.size == (140, 140)

    def test_crop_is_symmetric(self):
        """같은 crop_ratio 를 두 번 적용하면 동일한 결과가 나와야 한다."""
        spec = TransformSpec(type=TransformType.CROP_CENTER, crop_ratio=0.9)
        out1 = apply_transform(self.SRC, spec)
        out2 = apply_transform(self.SRC, spec)
        assert out1 == out2


class TestCropRandom:
    SRC = _make_test_jpeg(width=200, height=200, gradient=True)

    def test_80pct_random_crop_size(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.CROP_RANDOM, crop_ratio=0.80, seed=42))
        img = _open(out)
        assert img.size == (160, 160)

    def test_same_seed_reproducible(self):
        spec = TransformSpec(type=TransformType.CROP_RANDOM, crop_ratio=0.80, seed=42)
        out1 = apply_transform(self.SRC, spec)
        out2 = apply_transform(self.SRC, spec)
        assert out1 == out2

    def test_different_seed_different_result(self):
        spec1 = TransformSpec(type=TransformType.CROP_RANDOM, crop_ratio=0.80, seed=42)
        spec2 = TransformSpec(type=TransformType.CROP_RANDOM, crop_ratio=0.80, seed=99)
        out1 = apply_transform(self.SRC, spec1)
        out2 = apply_transform(self.SRC, spec2)
        # 다른 seed → 다른 픽셀 (동일할 확률은 무시할 수준)
        assert out1 != out2


# ---------------------------------------------------------------------------
# SNS 시뮬 테스트
# ---------------------------------------------------------------------------

class TestSnsInstagram:
    SRC = _make_test_jpeg(width=2000, height=1500)  # 큰 이미지 → 축소

    def test_output_is_jpeg(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.SNS_INSTAGRAM))
        assert _open(out).format == "JPEG"

    def test_max_dimension_1080(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.SNS_INSTAGRAM))
        img = _open(out)
        assert max(img.size) <= 1080

    def test_aspect_ratio_preserved(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.SNS_INSTAGRAM))
        img = _open(out)
        original_ratio = 2000 / 1500
        output_ratio = img.width / img.height
        assert abs(output_ratio - original_ratio) < 0.02

    def test_exif_stripped(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.SNS_INSTAGRAM))
        comment = _get_exif_user_comment(out)
        assert comment is None

    def test_small_image_not_upscaled(self):
        small = _make_test_jpeg(width=400, height=300)
        out = apply_transform(small, TransformSpec(type=TransformType.SNS_INSTAGRAM))
        img = _open(out)
        assert img.size == (400, 300)


class TestSnsTwitter:
    SRC = _make_test_jpeg(width=2000, height=1500)

    def test_max_dimension_1200(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.SNS_TWITTER))
        img = _open(out)
        assert max(img.size) <= 1200

    def test_output_is_jpeg(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.SNS_TWITTER))
        assert _open(out).format == "JPEG"

    def test_exif_stripped(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.SNS_TWITTER))
        assert _get_exif_user_comment(out) is None


class TestSnsKakaotalk:
    SRC = _make_test_jpeg(width=1600, height=1200)

    def test_chat_max_dimension_1000(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.SNS_KAKAOTALK_CHAT))
        img = _open(out)
        assert max(img.size) <= 1000

    def test_profile_is_480x480_square(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.SNS_KAKAOTALK_PROFILE))
        img = _open(out)
        assert img.size == (480, 480)

    def test_profile_exif_stripped(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.SNS_KAKAOTALK_PROFILE))
        assert _get_exif_user_comment(out) is None


# ---------------------------------------------------------------------------
# 스크린샷 시뮬 테스트
# ---------------------------------------------------------------------------

class TestScreenshot:
    SRC = _make_test_jpeg(width=400, height=300)

    def test_output_is_jpeg(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.SCREENSHOT, dpi=96))
        assert _open(out).format == "JPEG"

    def test_dimensions_unchanged(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.SCREENSHOT, dpi=96))
        img = _open(out)
        assert img.size == (400, 300)

    def test_exif_stripped(self):
        out = apply_transform(self.SRC, TransformSpec(type=TransformType.SCREENSHOT, dpi=96))
        assert _get_exif_user_comment(out) is None

    def test_96dpi_and_72dpi_work(self):
        for dpi in (96, 72):
            out = apply_transform(self.SRC, TransformSpec(type=TransformType.SCREENSHOT, dpi=dpi))
            assert len(out) > 0


# ---------------------------------------------------------------------------
# 배터리 상수 완전성 테스트
# ---------------------------------------------------------------------------

class TestTransformBattery:
    def test_battery_not_empty(self):
        assert len(TRANSFORM_BATTERY) > 0

    def test_battery_covers_all_transform_types(self):
        covered = {spec.type for spec in TRANSFORM_BATTERY}
        required = set(TransformType)
        assert required == covered, f"커버 안 된 타입: {required - covered}"

    def test_battery_has_5_jpeg_levels(self):
        jpeg_specs = [s for s in TRANSFORM_BATTERY if s.type == TransformType.JPEG_COMPRESS]
        assert len(jpeg_specs) == 5

    def test_battery_has_3_webp_levels(self):
        webp_specs = [s for s in TRANSFORM_BATTERY if s.type == TransformType.WEBP_CONVERT]
        assert len(webp_specs) == 3

    def test_battery_has_3_resize_levels(self):
        resize_specs = [s for s in TRANSFORM_BATTERY if s.type == TransformType.RESIZE]
        assert len(resize_specs) == 3

    def test_battery_labels_are_unique(self):
        labels = [spec.label() for spec in TRANSFORM_BATTERY]
        assert len(labels) == len(set(labels)), "중복 label 발견"

    def test_each_battery_spec_is_executable(self):
        src = _make_test_jpeg(width=512, height=512)
        for spec in TRANSFORM_BATTERY:
            out = apply_transform(src, spec)
            assert len(out) > 0, f"빈 출력: {spec.label()}"


# ---------------------------------------------------------------------------
# SNS 파라미터 카탈로그 테스트
# ---------------------------------------------------------------------------

class TestSnsParams:
    def test_all_major_platforms_documented(self):
        assert "instagram" in SNS_PARAMS
        assert "twitter_x" in SNS_PARAMS
        assert "kakaotalk_chat" in SNS_PARAMS
        assert "kakaotalk_profile" in SNS_PARAMS

    def test_all_platforms_strip_metadata(self):
        for platform, params in SNS_PARAMS.items():
            assert params.get("strips_exif") is True, f"{platform}: strips_exif 없음"
            assert params.get("strips_c2pa") is True, f"{platform}: strips_c2pa 없음"

    def test_instagram_max_1080(self):
        assert SNS_PARAMS["instagram"]["max_dimension_px"] == 1080

    def test_twitter_max_1200(self):
        assert SNS_PARAMS["twitter_x"]["max_dimension_px"] == 1200

    def test_kakaotalk_chat_max_1000(self):
        assert SNS_PARAMS["kakaotalk_chat"]["max_dimension_px"] == 1000

    def test_kakaotalk_profile_480(self):
        assert SNS_PARAMS["kakaotalk_profile"]["max_dimension_px"] == 480

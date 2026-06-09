"""W5 Task3 — koai_verify/pipeline.py 단위 테스트.

이미지 로드·검증·정규화 파이프라인 검증.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pytest
from PIL import Image as PILImage

from koai_verify.pipeline import (
    ImageFormat,
    ImageInput,
    ImageLoadError,
    _compute_sha256,
    _detect_format,
    load_from_bytes,
    load_from_path,
)

SAMPLES_DIR = Path(__file__).parent.parent / "fixtures" / "samples"


def _make_jpeg_bytes(width: int = 100, height: int = 80, quality: int = 85) -> bytes:
    img = PILImage.new("RGB", (width, height), color=(128, 64, 32))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _make_png_bytes(width: int = 50, height: int = 50) -> bytes:
    img = PILImage.new("RGB", (width, height), color=(0, 128, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_webp_bytes(width: int = 60, height: int = 40) -> bytes:
    img = PILImage.new("RGB", (width, height), color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=80)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# ImageFormat 열거형
# ---------------------------------------------------------------------------


class TestImageFormat:
    def test_jpeg_value(self):
        assert ImageFormat.JPEG == "jpeg"

    def test_png_value(self):
        assert ImageFormat.PNG == "png"

    def test_webp_value(self):
        assert ImageFormat.WEBP == "webp"

    def test_three_formats_defined(self):
        assert len(ImageFormat) == 3


# ---------------------------------------------------------------------------
# _detect_format
# ---------------------------------------------------------------------------


class TestDetectFormat:
    def test_jpeg_detected(self):
        assert _detect_format(_make_jpeg_bytes()) == ImageFormat.JPEG

    def test_png_detected(self):
        assert _detect_format(_make_png_bytes()) == ImageFormat.PNG

    def test_webp_detected(self):
        assert _detect_format(_make_webp_bytes()) == ImageFormat.WEBP

    def test_invalid_bytes_raises(self):
        with pytest.raises(ImageLoadError, match="포맷 탐지 실패"):
            _detect_format(b"not_an_image_at_all")

    def test_gif_not_supported(self):
        img = PILImage.new("RGB", (10, 10))
        buf = io.BytesIO()
        img.save(buf, format="GIF")
        with pytest.raises(ImageLoadError, match="지원하지 않는 포맷"):
            _detect_format(buf.getvalue())


# ---------------------------------------------------------------------------
# _compute_sha256
# ---------------------------------------------------------------------------


class TestComputeSha256:
    def test_returns_64_hex_chars(self):
        result = _compute_sha256(b"hello")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self):
        data = _make_jpeg_bytes()
        assert _compute_sha256(data) == _compute_sha256(data)

    def test_different_data_different_hash(self):
        a = _compute_sha256(b"hello")
        b = _compute_sha256(b"world")
        assert a != b

    def test_known_hash(self):
        expected = hashlib.sha256(b"koai").hexdigest()
        assert _compute_sha256(b"koai") == expected


# ---------------------------------------------------------------------------
# load_from_bytes
# ---------------------------------------------------------------------------


class TestLoadFromBytes:
    def test_jpeg_returns_image_input(self):
        result = load_from_bytes(_make_jpeg_bytes())
        assert isinstance(result, ImageInput)

    def test_format_detected_jpeg(self):
        result = load_from_bytes(_make_jpeg_bytes())
        assert result.format == ImageFormat.JPEG

    def test_format_detected_png(self):
        result = load_from_bytes(_make_png_bytes())
        assert result.format == ImageFormat.PNG

    def test_format_detected_webp(self):
        result = load_from_bytes(_make_webp_bytes())
        assert result.format == ImageFormat.WEBP

    def test_sha256_is_hex_64(self):
        result = load_from_bytes(_make_jpeg_bytes())
        assert len(result.sha256) == 64

    def test_dimensions_correct(self):
        result = load_from_bytes(_make_jpeg_bytes(width=120, height=80))
        assert result.width == 120
        assert result.height == 80

    def test_size_property(self):
        result = load_from_bytes(_make_jpeg_bytes(width=200, height=150))
        assert result.size == (200, 150)

    def test_byte_size(self):
        data = _make_jpeg_bytes()
        result = load_from_bytes(data)
        assert result.byte_size == len(data)

    def test_source_path_none_by_default(self):
        result = load_from_bytes(_make_jpeg_bytes())
        assert result.source_path is None

    def test_source_path_stored(self):
        result = load_from_bytes(_make_jpeg_bytes(), source_path="/tmp/test.jpg")
        assert result.source_path == "/tmp/test.jpg"

    def test_empty_bytes_raises(self):
        with pytest.raises(ImageLoadError, match="빈 이미지"):
            load_from_bytes(b"")

    def test_oversized_bytes_raises(self):
        large = b"X" * (51 * 1024 * 1024)
        with pytest.raises(ImageLoadError, match="크기 초과"):
            load_from_bytes(large)

    def test_image_input_is_frozen(self):
        result = load_from_bytes(_make_jpeg_bytes())
        with pytest.raises(Exception):
            result.format = ImageFormat.PNG  # type: ignore[misc]


# ---------------------------------------------------------------------------
# load_from_path
# ---------------------------------------------------------------------------


class TestLoadFromPath:
    def test_loads_real_fixture(self):
        path = SAMPLES_DIR / "stable_diffusion" / "stable_diffusion_01.jpg"
        result = load_from_path(path)
        assert result.format == ImageFormat.JPEG
        assert result.source_path == str(path)

    def test_nonexistent_path_raises(self, tmp_path):
        with pytest.raises(ImageLoadError, match="파일 없음"):
            load_from_path(tmp_path / "does_not_exist.jpg")

    def test_directory_path_raises(self, tmp_path):
        with pytest.raises(ImageLoadError, match="파일이 아님"):
            load_from_path(tmp_path)

    def test_url_raises_ssrf_guard(self):
        with pytest.raises(ImageLoadError, match="URL 로드 금지"):
            load_from_path("http://example.com/image.jpg")

    def test_https_url_raises_ssrf_guard(self):
        with pytest.raises(ImageLoadError, match="URL 로드 금지"):
            load_from_path("https://example.com/image.jpg")

    def test_returns_correct_sha256(self):
        path = SAMPLES_DIR / "stable_diffusion" / "stable_diffusion_01.jpg"
        data = path.read_bytes()
        expected_hash = hashlib.sha256(data).hexdigest()
        result = load_from_path(path)
        assert result.sha256 == expected_hash

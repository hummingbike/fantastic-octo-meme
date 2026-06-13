"""W17 — 채택 피드백 스프린트: Python SDK 오류 계층 및 JS SDK 오류 컨텍스트."""

from __future__ import annotations

import struct

import pytest

import koai_verify
from koai_verify.pipeline import (
    ImageCorruptedError,
    ImageLoadError,
    ImageNotFoundError,
    ImageTooLargeError,
    UnsupportedFormatError,
    UrlNotAllowedError,
    load_from_bytes,
    load_from_path,
)

# ---------------------------------------------------------------------------
# 오류 계층 구조 (isinstance 검사)
# ---------------------------------------------------------------------------


class TestErrorHierarchy:
    """모든 구체적 오류 클래스가 ImageLoadError 의 서브클래스임을 보장."""

    def test_url_not_allowed_is_image_load_error(self):
        assert issubclass(UrlNotAllowedError, ImageLoadError)

    def test_image_not_found_is_image_load_error(self):
        assert issubclass(ImageNotFoundError, ImageLoadError)

    def test_unsupported_format_is_image_load_error(self):
        assert issubclass(UnsupportedFormatError, ImageLoadError)

    def test_image_too_large_is_image_load_error(self):
        assert issubclass(ImageTooLargeError, ImageLoadError)

    def test_image_corrupted_is_image_load_error(self):
        assert issubclass(ImageCorruptedError, ImageLoadError)

    def test_image_load_error_is_value_error(self):
        assert issubclass(ImageLoadError, ValueError)

    def test_concrete_errors_are_value_error(self):
        for cls in (
            UrlNotAllowedError,
            ImageNotFoundError,
            UnsupportedFormatError,
            ImageTooLargeError,
            ImageCorruptedError,
        ):
            assert issubclass(cls, ValueError), f"{cls.__name__} 은 ValueError 서브클래스여야 함"


# ---------------------------------------------------------------------------
# UrlNotAllowedError
# ---------------------------------------------------------------------------


class TestUrlNotAllowedError:
    def test_http_url_raises_url_not_allowed(self):
        with pytest.raises(UrlNotAllowedError):
            load_from_path("http://example.com/image.jpg")

    def test_https_url_raises_url_not_allowed(self):
        with pytest.raises(UrlNotAllowedError):
            load_from_path("https://example.com/image.png")

    def test_ftp_url_raises_url_not_allowed(self):
        with pytest.raises(UrlNotAllowedError):
            load_from_path("ftp://files.example.com/image.webp")

    def test_url_error_is_subclass_of_image_load_error(self, tmp_path):
        with pytest.raises(ImageLoadError):
            load_from_path("http://example.com/image.jpg")

    def test_error_message_contains_url(self):
        url = "https://example.com/image.jpg"
        with pytest.raises(UrlNotAllowedError, match=url):
            load_from_path(url)


# ---------------------------------------------------------------------------
# ImageNotFoundError
# ---------------------------------------------------------------------------


class TestImageNotFoundError:
    def test_nonexistent_file_raises_not_found(self, tmp_path):
        with pytest.raises(ImageNotFoundError):
            load_from_path(tmp_path / "no_such_file.jpg")

    def test_directory_raises_not_found(self, tmp_path):
        with pytest.raises(ImageNotFoundError):
            load_from_path(tmp_path)

    def test_not_found_is_image_load_error(self, tmp_path):
        with pytest.raises(ImageLoadError):
            load_from_path(tmp_path / "ghost.jpg")

    def test_error_message_contains_path(self, tmp_path):
        p = tmp_path / "missing.png"
        with pytest.raises(ImageNotFoundError, match=str(p)):
            load_from_path(p)


# ---------------------------------------------------------------------------
# ImageTooLargeError
# ---------------------------------------------------------------------------


class TestImageTooLargeError:
    def test_oversized_bytes_raises_too_large(self):
        oversized = b"X" * (50 * 1024 * 1024 + 1)
        with pytest.raises(ImageTooLargeError):
            load_from_bytes(oversized)

    def test_too_large_is_image_load_error(self):
        oversized = b"X" * (50 * 1024 * 1024 + 1)
        with pytest.raises(ImageLoadError):
            load_from_bytes(oversized)

    def test_error_message_shows_size_mb(self):
        oversized = b"X" * (51 * 1024 * 1024)
        with pytest.raises(ImageTooLargeError, match="51"):
            load_from_bytes(oversized)


# ---------------------------------------------------------------------------
# ImageCorruptedError
# ---------------------------------------------------------------------------


class TestImageCorruptedError:
    def test_empty_bytes_raises_corrupted(self):
        with pytest.raises(ImageCorruptedError):
            load_from_bytes(b"")

    def test_random_bytes_raises_corrupted(self):
        with pytest.raises(ImageCorruptedError):
            load_from_bytes(b"\x00\x01\x02\x03\x04\x05garbage")

    def test_corrupted_is_image_load_error(self):
        with pytest.raises(ImageLoadError):
            load_from_bytes(b"not-an-image")


# ---------------------------------------------------------------------------
# UnsupportedFormatError
# ---------------------------------------------------------------------------


def _make_bmp_bytes() -> bytes:
    """유효하지만 지원하지 않는 BMP 이미지 bytes 생성."""

    width, height = 2, 2
    row_size = (width * 3 + 3) & ~3
    pixel_data = b"\xff\x00\x00" * width
    pixel_data += b"\x00" * (row_size - width * 3)
    pixel_data = pixel_data * height
    file_size = 54 + len(pixel_data)
    header = struct.pack(
        "<2sIHHIIIIHHIIIIII",
        b"BM",
        file_size,
        0,
        0,
        54,
        40,
        width,
        height,
        1,
        24,
        0,
        len(pixel_data),
        2835,
        2835,
        0,
        0,
    )
    return header + pixel_data


class TestUnsupportedFormatError:
    def test_bmp_raises_unsupported_format(self):
        bmp = _make_bmp_bytes()
        with pytest.raises(UnsupportedFormatError):
            load_from_bytes(bmp)

    def test_unsupported_is_image_load_error(self):
        bmp = _make_bmp_bytes()
        with pytest.raises(ImageLoadError):
            load_from_bytes(bmp)

    def test_error_message_lists_supported_formats(self):
        bmp = _make_bmp_bytes()
        with pytest.raises(UnsupportedFormatError, match="JPEG|PNG|WEBP"):
            load_from_bytes(bmp)

    def test_error_message_contains_unsupported_format_name(self):
        bmp = _make_bmp_bytes()
        with pytest.raises(UnsupportedFormatError, match="BMP"):
            load_from_bytes(bmp)


# ---------------------------------------------------------------------------
# 공개 API 노출 확인 (import koai_verify)
# ---------------------------------------------------------------------------


class TestPublicApiExport:
    def test_image_load_error_exported(self):
        assert hasattr(koai_verify, "ImageLoadError")

    def test_image_not_found_exported(self):
        assert hasattr(koai_verify, "ImageNotFoundError")

    def test_url_not_allowed_exported(self):
        assert hasattr(koai_verify, "UrlNotAllowedError")

    def test_unsupported_format_exported(self):
        assert hasattr(koai_verify, "UnsupportedFormatError")

    def test_image_too_large_exported(self):
        assert hasattr(koai_verify, "ImageTooLargeError")

    def test_image_corrupted_exported(self):
        assert hasattr(koai_verify, "ImageCorruptedError")

    def test_all_error_classes_in_dunder_all(self):
        for name in (
            "ImageLoadError",
            "ImageNotFoundError",
            "UrlNotAllowedError",
            "UnsupportedFormatError",
            "ImageTooLargeError",
            "ImageCorruptedError",
        ):
            assert name in koai_verify.__all__, f"{name} 이 __all__ 에 없음"

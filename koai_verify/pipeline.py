"""W5 — 이미지 입력 파이프라인.

이미지를 로드·검증·정규화하고 탐지 엔진에 전달하기 전 공통 전처리를 수행한다.

설계 제약:
  - 외부 URL fetch 금지 (SSRF 방지) — 파일 경로만 수신
  - 원본 이미지 데이터 리포트 포함 금지 — 해시(sha256)만 사용
  - 최대 이미지 크기: 50MB (DoS 방지)
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Union

from PIL import Image as PILImage


class ImageFormat(str, Enum):
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"


_FORMAT_MAP: dict[str, ImageFormat] = {
    "JPEG": ImageFormat.JPEG,
    "PNG": ImageFormat.PNG,
    "WEBP": ImageFormat.WEBP,
}

_MAX_BYTES = 50 * 1024 * 1024  # 50 MB


class ImageLoadError(ValueError):
    """이미지 로드 또는 검증 실패 — 모든 파이프라인 오류의 베이스 클래스."""


class UrlNotAllowedError(ImageLoadError):
    """URL 로드 시도 거부 (SSRF 방지)."""


class ImageNotFoundError(ImageLoadError):
    """파일이 존재하지 않거나 디렉터리를 가리킴."""


class UnsupportedFormatError(ImageLoadError):
    """지원하지 않는 이미지 포맷."""


class ImageTooLargeError(ImageLoadError):
    """이미지 파일 크기가 50 MB 제한을 초과함."""


class ImageCorruptedError(ImageLoadError):
    """이미지 파일이 손상되어 디코딩할 수 없음."""


@dataclass(frozen=True)
class ImageInput:
    """파이프라인 입력 단위.

    Attributes:
        image_bytes: 원본 이미지 bytes (메모리에만 보관, 리포트에 미포함)
        format: 탐지된 이미지 포맷
        sha256: 원본 이미지 sha256 해시 (리포트용 식별자)
        width: 픽셀 너비
        height: 픽셀 높이
        source_path: 로드 출처 (파일 경로, 없으면 None)
    """

    image_bytes: bytes
    format: ImageFormat
    sha256: str
    width: int
    height: int
    source_path: str | None = None

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def byte_size(self) -> int:
        return len(self.image_bytes)


def load_from_path(path: Union[str, Path]) -> ImageInput:
    """파일 경로에서 이미지를 로드해 ImageInput 을 반환한다.

    URL 또는 http/https 스킴 경로는 거부한다 (SSRF 방지).
    """
    # SSRF 방지: Path() 변환 전에 원본 문자열로 검사
    # (Path("http://...") 는 "http:/..." 로 정규화되어 // 비교가 깨짐)
    raw_str = str(path)
    if raw_str.startswith(("http://", "https://", "ftp://")):
        raise UrlNotAllowedError(f"URL 로드 금지 — 파일 경로만 허용합니다 (SSRF 방지): {raw_str}")

    path = Path(path)

    if not path.exists():
        raise ImageNotFoundError(f"파일 없음: {path}")

    if not path.is_file():
        raise ImageNotFoundError(f"파일이 아님 (디렉터리?): {path}")

    raw = path.read_bytes()
    return load_from_bytes(raw, source_path=str(path))


def load_from_bytes(image_bytes: bytes, source_path: str | None = None) -> ImageInput:
    """bytes 에서 이미지를 로드해 ImageInput 을 반환한다."""
    if not image_bytes:
        raise ImageCorruptedError("빈 이미지 데이터")

    if len(image_bytes) > _MAX_BYTES:
        raise ImageTooLargeError(f"이미지 크기 초과: {len(image_bytes) / 1024 / 1024:.1f}MB > 50MB 제한")

    fmt = _detect_format(image_bytes)
    sha256 = _compute_sha256(image_bytes)
    width, height = _read_dimensions(image_bytes)

    return ImageInput(
        image_bytes=image_bytes,
        format=fmt,
        sha256=sha256,
        width=width,
        height=height,
        source_path=source_path,
    )


def _detect_format(image_bytes: bytes) -> ImageFormat:
    """이미지 bytes 에서 포맷을 탐지한다."""
    try:
        img = PILImage.open(io.BytesIO(image_bytes))
        pil_fmt = img.format
    except Exception as e:
        raise ImageCorruptedError(f"이미지 디코딩 실패 — 파일이 손상되었거나 지원하지 않는 포맷: {e}") from e

    if pil_fmt not in _FORMAT_MAP:
        supported = ", ".join(_FORMAT_MAP.keys())
        raise UnsupportedFormatError(
            f"지원하지 않는 포맷: {pil_fmt!r} (지원 포맷: {supported})\n" "PNG · JPEG · WebP 이미지를 사용하세요."
        )

    return _FORMAT_MAP[pil_fmt]


def _compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_dimensions(image_bytes: bytes) -> tuple[int, int]:
    try:
        img = PILImage.open(io.BytesIO(image_bytes))
        return img.size  # (width, height)
    except Exception as e:
        raise ImageCorruptedError(f"이미지 크기 읽기 실패: {e}") from e

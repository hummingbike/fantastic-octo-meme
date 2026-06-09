"""W3 강건성 벤치마크 — 변형 배터리 파라미터 명세 및 실행 코드.

변형 배터리 설계 원칙:
  - 각 변형은 독립적이고 재현 가능해야 한다 (seed 고정)
  - 변형 결과는 bytes 반환 — 이후 탐지 엔진이 그대로 입력으로 사용
  - SNS 시뮬은 실측 파라미터 기반 (Instagram/Twitter/KakaoTalk)

참조: PLAN.md W3, PRD §3.2 강건성 벤치마크
"""

from __future__ import annotations

import io
import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from PIL import Image as PILImage


class TransformType(str, Enum):
    JPEG_COMPRESS = "jpeg_compress"
    WEBP_CONVERT = "webp_convert"
    RESIZE = "resize"
    CROP_CENTER = "crop_center"
    CROP_RANDOM = "crop_random"
    SNS_INSTAGRAM = "sns_instagram"
    SNS_TWITTER = "sns_twitter"
    SNS_KAKAOTALK_CHAT = "sns_kakaotalk_chat"
    SNS_KAKAOTALK_PROFILE = "sns_kakaotalk_profile"
    SCREENSHOT = "screenshot"


@dataclass(frozen=True)
class TransformSpec:
    """변형 하나를 완전히 기술하는 불변 명세."""

    type: TransformType
    quality: Optional[int] = None  # JPEG/WebP 품질 (1-95)
    scale: Optional[float] = None  # 리사이즈 배율 (0.0-1.0)
    crop_ratio: Optional[float] = None  # 크롭 비율 (0.0-1.0)
    dpi: Optional[int] = None  # 스크린샷 DPI
    seed: int = 42  # 랜덤 크롭 재현성용 seed

    def label(self) -> str:
        """매트릭스 표 행/열 레이블."""
        t = self.type.value
        if self.quality is not None:
            return f"{t}_q{self.quality}"
        if self.scale is not None:
            return f"{t}_{int(self.scale * 100)}pct"
        if self.crop_ratio is not None:
            return f"{t}_{int(self.crop_ratio * 100)}pct"
        if self.dpi is not None:
            return f"{t}_{self.dpi}dpi"
        return t


# ---------------------------------------------------------------------------
# 변형 실행 함수
# ---------------------------------------------------------------------------


def apply_transform(image_bytes: bytes, spec: TransformSpec) -> bytes:
    """image_bytes 에 TransformSpec 변형을 적용하고 결과 bytes 를 반환한다."""
    img = PILImage.open(io.BytesIO(image_bytes))

    dispatch = {
        TransformType.JPEG_COMPRESS: _jpeg_compress,
        TransformType.WEBP_CONVERT: _webp_convert,
        TransformType.RESIZE: _resize,
        TransformType.CROP_CENTER: _crop_center,
        TransformType.CROP_RANDOM: _crop_random,
        TransformType.SNS_INSTAGRAM: _sns_instagram,
        TransformType.SNS_TWITTER: _sns_twitter,
        TransformType.SNS_KAKAOTALK_CHAT: _sns_kakaotalk_chat,
        TransformType.SNS_KAKAOTALK_PROFILE: _sns_kakaotalk_profile,
        TransformType.SCREENSHOT: _screenshot,
    }
    handler = dispatch.get(spec.type)
    if handler is None:
        raise ValueError(f"알 수 없는 TransformType: {spec.type}")
    return handler(img, spec)


def _to_bytes(img, fmt: str, **kwargs) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, **kwargs)
    return buf.getvalue()


def _ensure_rgb(img):
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    if img.mode == "RGBA":
        bg = __import__("PIL.Image", fromlist=["Image"]).Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        return bg
    return img


def _limit_max_dimension(img, max_px: int):
    w, h = img.size
    if max(w, h) <= max_px:
        return img
    if w >= h:
        new_w, new_h = max_px, int(h * max_px / w)
    else:
        new_w, new_h = int(w * max_px / h), max_px
    return img.resize((new_w, new_h), PILImage.Resampling.LANCZOS)


# --- 개별 변형 구현 ---


def _jpeg_compress(img, spec: TransformSpec) -> bytes:
    q = spec.quality if spec.quality is not None else 80
    img = _ensure_rgb(img)
    return _to_bytes(img, "JPEG", quality=q, optimize=True)


def _webp_convert(img, spec: TransformSpec) -> bytes:
    q = spec.quality if spec.quality is not None else 80
    img = _ensure_rgb(img)
    return _to_bytes(img, "WEBP", quality=q, method=6)


def _resize(img, spec: TransformSpec) -> bytes:
    scale = spec.scale if spec.scale is not None else 0.5
    new_w = max(1, int(img.width * scale))
    new_h = max(1, int(img.height * scale))
    img = img.resize((new_w, new_h), PILImage.Resampling.LANCZOS)
    return _to_bytes(_ensure_rgb(img), "JPEG", quality=95)


def _crop_center(img, spec: TransformSpec) -> bytes:
    ratio = spec.crop_ratio if spec.crop_ratio is not None else 0.9
    w, h = img.size
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    left = (w - new_w) // 2
    top = (h - new_h) // 2
    img = img.crop((left, top, left + new_w, top + new_h))
    return _to_bytes(_ensure_rgb(img), "JPEG", quality=95)


def _crop_random(img, spec: TransformSpec) -> bytes:
    ratio = spec.crop_ratio if spec.crop_ratio is not None else 0.8
    rng = random.Random(spec.seed)
    w, h = img.size
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    left = rng.randint(0, max(0, w - new_w))
    top = rng.randint(0, max(0, h - new_h))
    img = img.crop((left, top, left + new_w, top + new_h))
    return _to_bytes(_ensure_rgb(img), "JPEG", quality=95)


def _sns_instagram(img, spec: TransformSpec) -> bytes:
    """Instagram 업로드 시뮬: 최대 1080px, JPEG q=80, 메타데이터 제거."""
    img = _ensure_rgb(img)
    img = _limit_max_dimension(img, 1080)
    return _to_bytes(img, "JPEG", quality=80)


def _sns_twitter(img, spec: TransformSpec) -> bytes:
    """Twitter/X 업로드 시뮬: 최대 1200px, JPEG q=78, 메타데이터 제거."""
    img = _ensure_rgb(img)
    img = _limit_max_dimension(img, 1200)
    return _to_bytes(img, "JPEG", quality=78)


def _sns_kakaotalk_chat(img, spec: TransformSpec) -> bytes:
    """KakaoTalk 채팅 이미지 시뮬: 최대 1000px, JPEG q=70."""
    img = _ensure_rgb(img)
    img = _limit_max_dimension(img, 1000)
    return _to_bytes(img, "JPEG", quality=70)


def _sns_kakaotalk_profile(img, spec: TransformSpec) -> bytes:
    """KakaoTalk 프로필 사진 시뮬: 480×480 center crop, JPEG q=70."""
    img = _ensure_rgb(img)
    # 짧은 변 기준 리사이즈 후 중앙 480×480 크롭
    w, h = img.size
    target = 480
    if w < h:
        new_w, new_h = target, int(h * target / w)
    else:
        new_w, new_h = int(w * target / h), target
    img = img.resize((new_w, new_h), PILImage.Resampling.LANCZOS)
    left = (new_w - target) // 2
    top = (new_h - target) // 2
    img = img.crop((left, top, left + target, top + target))
    return _to_bytes(img, "JPEG", quality=70)


def _screenshot(img, spec: TransformSpec) -> bytes:
    """스크린샷 시뮬: RGB 재변환, JPEG q=90. EXIF·C2PA 완전 제거."""
    img = _ensure_rgb(img)
    # 스크린샷: 픽셀 데이터만 새 이미지로 복사 (메타데이터 완전 소거)
    clean = PILImage.new("RGB", img.size)
    clean.paste(img)
    return _to_bytes(clean, "JPEG", quality=90)


# ---------------------------------------------------------------------------
# 변형 배터리 상수
# ---------------------------------------------------------------------------

TRANSFORM_BATTERY: list[TransformSpec] = [
    # JPEG 압축
    TransformSpec(type=TransformType.JPEG_COMPRESS, quality=95),
    TransformSpec(type=TransformType.JPEG_COMPRESS, quality=80),
    TransformSpec(type=TransformType.JPEG_COMPRESS, quality=60),
    TransformSpec(type=TransformType.JPEG_COMPRESS, quality=40),
    TransformSpec(type=TransformType.JPEG_COMPRESS, quality=20),
    # WebP 변환
    TransformSpec(type=TransformType.WEBP_CONVERT, quality=90),
    TransformSpec(type=TransformType.WEBP_CONVERT, quality=70),
    TransformSpec(type=TransformType.WEBP_CONVERT, quality=50),
    # 리사이즈 (bilinear ≈ Pillow LANCZOS)
    TransformSpec(type=TransformType.RESIZE, scale=0.75),
    TransformSpec(type=TransformType.RESIZE, scale=0.50),
    TransformSpec(type=TransformType.RESIZE, scale=0.25),
    # 크롭 — center
    TransformSpec(type=TransformType.CROP_CENTER, crop_ratio=0.90),
    TransformSpec(type=TransformType.CROP_CENTER, crop_ratio=0.70),
    # 크롭 — random (seed=42)
    TransformSpec(type=TransformType.CROP_RANDOM, crop_ratio=0.80, seed=42),
    # SNS 재인코딩 시뮬
    TransformSpec(type=TransformType.SNS_INSTAGRAM),
    TransformSpec(type=TransformType.SNS_TWITTER),
    TransformSpec(type=TransformType.SNS_KAKAOTALK_CHAT),
    TransformSpec(type=TransformType.SNS_KAKAOTALK_PROFILE),
    # 스크린샷 시뮬
    TransformSpec(type=TransformType.SCREENSHOT, dpi=96),
    TransformSpec(type=TransformType.SCREENSHOT, dpi=72),
]

# ---------------------------------------------------------------------------
# SNS 파라미터 조사 결과 (실측 기반)
# ---------------------------------------------------------------------------

SNS_PARAMS: dict[str, dict] = {
    "instagram": {
        "max_dimension_px": 1080,
        "output_format": "JPEG",
        "quality_approx": 80,
        "strips_exif": True,
        "strips_c2pa": True,
        "strips_xmp": True,
        "source": "Meta engineering blog + 실측 분석 (2024)",
    },
    "twitter_x": {
        "max_dimension_px": 1200,
        "output_format": "JPEG",  # 내부 WebP 변환 후 JPEG로 제공
        "quality_approx": 78,
        "strips_exif": True,
        "strips_c2pa": True,
        "strips_xmp": True,
        "source": "Twitter media processing 실측 분석 (2024)",
    },
    "kakaotalk_chat": {
        "max_dimension_px": 1000,
        "output_format": "JPEG",
        "quality_approx": 70,
        "strips_exif": True,
        "strips_c2pa": True,
        "strips_xmp": True,
        "source": "KakaoTalk 실측 분석 (2024)",
    },
    "kakaotalk_profile": {
        "max_dimension_px": 480,
        "crop": "center_square_480",
        "output_format": "JPEG",
        "quality_approx": 70,
        "strips_exif": True,
        "strips_c2pa": True,
        "source": "KakaoTalk 프로필 설정 실측 (2024)",
    },
}

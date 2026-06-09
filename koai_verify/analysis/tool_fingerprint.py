"""W4 — 도구별 AI 표시 메타데이터 분석 모듈.

이미지 bytes 에서 AI 표시 마킹을 읽고, 도구 핑거프린트와 컴플라이언스 갭을 분류한다.
W6/W7 탐지 엔진의 전신(前身) — Phase 0 분석 단계용.

설계 제약:
  - UNKNOWN 을 명시적으로 반환 — 과대주장 금지
  - OCR 탐지는 W7 이후 — 여기서는 EXIF/C2PA만 처리
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MarkingPresence(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    UNKNOWN = "UNKNOWN"  # 탐지 불가 (비공개 API 등)


class GapCategory(str, Enum):
    """컴플라이언스 갭 분류 (R-01~R-05 연계)."""

    NO_MARKING = "no_marking"  # R-05: 어떤 표시도 없음
    INVISIBLE_ONLY = "invisible_only"  # R-03 위험: 비가시만, 안내 없음
    PARTIAL = "partial"  # 일부 마킹 있으나 불완전
    DETECTABLE = "detectable"  # 하나 이상 탐지 가능한 마킹 있음
    UNKNOWN = "unknown"  # 탐지 자체 불가 (한국 도구 미수집 등)


@dataclass
class ToolFingerprint:
    """도구 하나의 AI 표시 마킹 핑거프린트."""

    tool_name: str
    c2pa: MarkingPresence
    exif_ai: MarkingPresence
    visible_label: MarkingPresence  # W7 이전: NOT_FOUND 고정
    open_watermark: MarkingPresence  # W7 이전: UNKNOWN 고정
    exif_software: Optional[str] = None
    exif_user_comment_text: Optional[str] = None
    gap_category: GapCategory = GapCategory.UNKNOWN
    notes: str = ""

    def any_marking_found(self) -> bool:
        return any(m == MarkingPresence.FOUND for m in (self.c2pa, self.exif_ai, self.visible_label))

    def any_invisible_found(self) -> bool:
        return any(m == MarkingPresence.FOUND for m in (self.c2pa, self.exif_ai, self.open_watermark))


# ---------------------------------------------------------------------------
# AI 키워드 (EXIF 탐지용)
# ---------------------------------------------------------------------------

_AI_SOFTWARE_KEYWORDS = [
    b"stable diffusion",
    b"comfyui",
    b"midjourney",
    b"dall-e",
    b"firefly",
    b"ai generated",
    b"ai",
    b"dream",
    b"diffusion",
]

_AI_USER_COMMENT_KEYWORDS = [
    "ai generated",
    "aigc",
    "artificial intelligence",
    "ai 생성",
    "steps:",
    "sampler:",
    "model:",
    "nodes",  # SD/ComfyUI 파라미터
]

_USER_COMMENT_ASCII_PREFIX = b"ASCII\x00\x00\x00"
_USER_COMMENT_UNICODE_PREFIX = b"UNICODE\x00"


def _decode_user_comment(raw: bytes) -> Optional[str]:
    if not raw:
        return None
    for prefix, enc in (
        (_USER_COMMENT_ASCII_PREFIX, "ascii"),
        (_USER_COMMENT_UNICODE_PREFIX, "utf-16-le"),
    ):
        if raw.startswith(prefix):
            try:
                return raw[len(prefix) :].decode(enc, errors="ignore").rstrip("\x00").strip()
            except Exception:
                return None
    return raw.decode("latin-1", errors="ignore").strip() or None


def _has_ai_software(software_bytes: bytes) -> bool:
    lower = software_bytes.lower()
    return any(kw in lower for kw in _AI_SOFTWARE_KEYWORDS)


def _has_ai_user_comment(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _AI_USER_COMMENT_KEYWORDS)


# ---------------------------------------------------------------------------
# EXIF 분석
# ---------------------------------------------------------------------------


def _analyze_exif(image_bytes: bytes) -> tuple[MarkingPresence, Optional[str], Optional[str]]:
    """EXIF 기반 AI 표시 분석.

    Returns:
        (presence, exif_software, user_comment_text)
    """
    try:
        import piexif
    except ImportError:
        return MarkingPresence.UNKNOWN, None, None

    try:
        exif = piexif.load(image_bytes)
    except Exception:
        return MarkingPresence.NOT_FOUND, None, None

    software_raw = exif.get("0th", {}).get(piexif.ImageIFD.Software, b"")
    software_str = software_raw.decode("latin-1", errors="ignore").strip() if software_raw else None
    has_soft = bool(software_raw) and _has_ai_software(software_raw)

    uc_raw = exif.get("Exif", {}).get(piexif.ExifIFD.UserComment, b"")
    uc_text = _decode_user_comment(uc_raw) if uc_raw else None
    has_uc = bool(uc_text) and _has_ai_user_comment(uc_text)

    image_desc = exif.get("0th", {}).get(piexif.ImageIFD.ImageDescription, b"")
    image_desc_str = image_desc.decode("latin-1", errors="ignore").strip() if image_desc else ""
    has_desc = bool(image_desc_str) and any(kw in image_desc_str.lower() for kw in ("ai generated", "ai 생성"))

    if has_soft or has_uc or has_desc:
        return MarkingPresence.FOUND, software_str, uc_text
    else:
        return MarkingPresence.NOT_FOUND, software_str, uc_text


# ---------------------------------------------------------------------------
# C2PA 분석
# ---------------------------------------------------------------------------


def _analyze_c2pa(image_bytes: bytes) -> MarkingPresence:
    try:
        import c2pa
    except ImportError:
        return MarkingPresence.UNKNOWN

    try:
        buf = io.BytesIO(image_bytes)
        with c2pa.Reader("image/jpeg", buf) as reader:
            manifest_json = reader.json()
            if manifest_json:
                return MarkingPresence.FOUND
            return MarkingPresence.NOT_FOUND
    except c2pa.C2paError:
        return MarkingPresence.NOT_FOUND
    except Exception:
        return MarkingPresence.UNKNOWN


# ---------------------------------------------------------------------------
# 갭 분류
# ---------------------------------------------------------------------------


def _classify_gap(fp: ToolFingerprint) -> GapCategory:
    """R-01~R-05 기반 갭 분류."""
    if fp.c2pa == MarkingPresence.UNKNOWN and fp.exif_ai == MarkingPresence.UNKNOWN:
        return GapCategory.UNKNOWN

    visible_found = fp.visible_label == MarkingPresence.FOUND
    c2pa_found = fp.c2pa == MarkingPresence.FOUND
    exif_found = fp.exif_ai == MarkingPresence.FOUND

    if visible_found:
        # R-04 충족 → 가시 표시 있음
        return GapCategory.DETECTABLE

    if c2pa_found or exif_found:
        # 비가시 마킹만 있음 → R-03 위험 (사람 인식 안내 없으면 불충족)
        return GapCategory.INVISIBLE_ONLY

    # 어떤 탐지 가능 마킹도 없음 → R-05
    return GapCategory.NO_MARKING


# ---------------------------------------------------------------------------
# 메인 분석 함수
# ---------------------------------------------------------------------------


def fingerprint_image(image_bytes: bytes, tool_name: str = "unknown") -> ToolFingerprint:
    """이미지 bytes 를 분석해 ToolFingerprint 를 반환한다.

    W7 이전: OCR(가시 라벨)·오픈 워터마크 탐지 미구현 → NOT_FOUND/UNKNOWN 고정.
    """
    c2pa_result = _analyze_c2pa(image_bytes)
    exif_result, software, uc_text = _analyze_exif(image_bytes)

    fp = ToolFingerprint(
        tool_name=tool_name,
        c2pa=c2pa_result,
        exif_ai=exif_result,
        visible_label=MarkingPresence.NOT_FOUND,  # W7 구현 예정
        open_watermark=MarkingPresence.UNKNOWN,  # W7 구현 예정
        exif_software=software,
        exif_user_comment_text=uc_text,
        gap_category=GapCategory.UNKNOWN,
    )
    fp.gap_category = _classify_gap(fp)
    return fp


# ---------------------------------------------------------------------------
# 도구별 알려진 특성 카탈로그 (공개 문서 기반)
# ---------------------------------------------------------------------------

KNOWN_TOOL_CATALOG: dict[str, dict] = {
    "stable_diffusion": {
        "marking_types": ["exif_software", "exif_user_comment"],
        "c2pa_support": False,
        "known_gap": GapCategory.INVISIBLE_ONLY,
        "r03_risk": True,
        "notes": "AUTOMATIC1111: Software+UserComment. 비가시만 있고 안내 없음 → R-03 불충족 위험.",
    },
    "comfyui": {
        "marking_types": ["exif_user_comment"],
        "c2pa_support": False,
        "known_gap": GapCategory.INVISIBLE_ONLY,
        "r03_risk": True,
        "notes": "UserComment에 workflow JSON. 안내 없음 → R-03 불충족 위험.",
    },
    "adobe_firefly": {
        "marking_types": ["c2pa"],
        "c2pa_support": True,
        "known_gap": GapCategory.INVISIBLE_ONLY,
        "r03_risk": True,
        "notes": "C2PA 있음. SNS 재인코딩 후 C2PA 유실 → SNS 공유 시 R-03 위험.",
    },
    "midjourney": {
        "marking_types": [],
        "c2pa_support": False,
        "known_gap": GapCategory.NO_MARKING,
        "r03_risk": False,  # R-05 직접 불충족
        "notes": "어떤 AI 마킹도 없음. R-05 불충족.",
    },
    "dall_e_3": {
        "marking_types": [],
        "c2pa_support": False,
        "known_gap": GapCategory.NO_MARKING,
        "r03_risk": False,
        "notes": "EXIF AI 마킹 없음. C2PA 미지원(2026 기준). R-05 불충족.",
    },
    "drapart": {
        "marking_types": [],
        "c2pa_support": None,  # 미확인
        "known_gap": GapCategory.UNKNOWN,
        "r03_risk": None,
        "notes": "W4 실제 샘플 수집 필요. SD 기반 가능성 있음.",
    },
    "genape": {
        "marking_types": [],
        "c2pa_support": None,
        "known_gap": GapCategory.UNKNOWN,
        "r03_risk": None,
        "notes": "W4 실제 샘플 수집 필요.",
    },
    "vela": {
        "marking_types": [],
        "c2pa_support": None,
        "known_gap": GapCategory.UNKNOWN,
        "r03_risk": None,
        "notes": "W4 실제 샘플 수집 필요.",
    },
    "jeditor": {
        "marking_types": [],
        "c2pa_support": None,
        "known_gap": GapCategory.UNKNOWN,
        "r03_risk": None,
        "notes": "W4 실제 샘플 수집 필요. 영상/이미지 편집 도구.",
    },
}

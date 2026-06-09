"""W6 — C2PA 매니페스트 탐지 엔진.

c2pa-python 라이브러리로 JPEG/PNG/WebP 이미지에서 C2PA 매니페스트 유무를 판정한다.
"""

from __future__ import annotations

import io
import json
from typing import Optional

import c2pa
from PIL import Image, UnidentifiedImageError

from .base import DetectorBase
from .result import DetectionResult, DetectorOutput

_PILLOW_TO_MIME: dict[str, str] = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


class C2PADetector(DetectorBase):
    """C2PA 매니페스트 유무를 탐지한다.

    FOUND    : 유효한 C2PA 매니페스트 존재
    NOT_FOUND: 매니페스트 없음 (c2pa.C2paError)
    UNKNOWN  : 지원하지 않는 포맷이거나 매니페스트 JSON 파싱 불가
    """

    @property
    def name(self) -> str:
        return "c2pa"

    def detect(self, image_bytes: bytes) -> DetectorOutput:
        mime = _detect_mime(image_bytes)
        if mime is None:
            return DetectorOutput(
                result=DetectionResult.UNKNOWN,
                detector_name=self.name,
                details={"reason": "unsupported_format"},
            )

        buf = io.BytesIO(image_bytes)
        try:
            with c2pa.Reader(mime, buf) as reader:
                manifest_json = reader.json()
        except c2pa.C2paError:
            return DetectorOutput(
                result=DetectionResult.NOT_FOUND,
                detector_name=self.name,
            )

        try:
            manifest = json.loads(manifest_json)
        except (json.JSONDecodeError, TypeError):
            return DetectorOutput(
                result=DetectionResult.UNKNOWN,
                detector_name=self.name,
                details={"reason": "invalid_manifest_json"},
            )

        return DetectorOutput(
            result=DetectionResult.FOUND,
            detector_name=self.name,
            details=_extract_manifest_details(manifest),
        )


def _detect_mime(image_bytes: bytes) -> Optional[str]:
    """이미지 bytes 에서 MIME 타입을 탐지한다. 지원하지 않으면 None."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        return _PILLOW_TO_MIME.get(img.format)
    except (UnidentifiedImageError, Exception):
        return None


def _extract_manifest_details(manifest: dict) -> dict:
    """C2PA manifest 딕셔너리에서 리포트용 상세 정보를 추출한다."""
    manifests = manifest.get("manifests", {})
    active_id: Optional[str] = manifest.get("active_manifest")
    details: dict = {
        "manifest_count": len(manifests),
        "active_manifest": active_id,
    }
    if active_id and active_id in manifests:
        active = manifests[active_id]
        details["claim_generator"] = active.get("claim_generator")
        assertions = active.get("assertions", [])
        details["assertion_count"] = len(assertions)
        details["assertion_labels"] = [a["label"] for a in assertions if isinstance(a, dict) and "label" in a]
    return details

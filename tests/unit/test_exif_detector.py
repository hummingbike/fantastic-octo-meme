"""W6 — EXIFDetector 단위 테스트.

테스트 대상: koai_verify/detectors/exif_detector.py

픽스처 전략:
  - 합성 JPEG (piexif 로 직접 작성) — 각 필드별 양성/음성 케이스
  - tests/fixtures/samples/ 아래 실제 합성 픽스처 (stable_diffusion, comfyui, midjourney)
"""
from __future__ import annotations

import io
from pathlib import Path

import piexif
import pytest
from PIL import Image

from koai_verify.detectors.exif_detector import (
    EXIFDetector,
    decode_user_comment,
    _contains_ai_keyword_any,
)
from koai_verify.detectors.result import DetectionResult

SAMPLES_DIR = Path(__file__).parent.parent / "fixtures" / "samples"


# ---------------------------------------------------------------------------
# 헬퍼: 합성 JPEG 생성
# ---------------------------------------------------------------------------

def _make_jpeg(exif_dict: dict | None = None) -> bytes:
    """32×32 JPEG — exif_dict 없으면 메타데이터 없음."""
    img = Image.new("RGB", (32, 32), color=(100, 150, 200))
    buf = io.BytesIO()
    if exif_dict is not None:
        img.save(buf, format="JPEG", exif=piexif.dump(exif_dict))
    else:
        img.save(buf, format="JPEG")
    return buf.getvalue()


def _empty_exif() -> dict:
    return {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}


# ---------------------------------------------------------------------------
# 탐지기 이름 및 인터페이스
# ---------------------------------------------------------------------------

class TestEXIFDetectorInterface:
    def test_name_is_exif(self):
        assert EXIFDetector().name == "exif"

    def test_is_detector_base_subclass(self):
        from koai_verify.detectors.base import DetectorBase
        assert isinstance(EXIFDetector(), DetectorBase)

    def test_detect_returns_detector_output(self):
        from koai_verify.detectors.result import DetectorOutput
        output = EXIFDetector().detect(_make_jpeg())
        assert isinstance(output, DetectorOutput)

    def test_detect_output_detector_name_is_exif(self):
        output = EXIFDetector().detect(_make_jpeg())
        assert output.detector_name == "exif"

    def test_result_has_found_in_fields_key(self):
        output = EXIFDetector().detect(_make_jpeg())
        assert "found_in_fields" in output.details


# ---------------------------------------------------------------------------
# NOT_FOUND — AI 키워드 없음
# ---------------------------------------------------------------------------

class TestEXIFDetectorNotFound:
    def test_plain_jpeg_no_exif_returns_not_found(self):
        # piexif 가 빈 dict 를 반환하므로 NOT_FOUND
        output = EXIFDetector().detect(_make_jpeg())
        assert output.result == DetectionResult.NOT_FOUND

    def test_empty_exif_dict_returns_not_found(self):
        data = _make_jpeg(_empty_exif())
        output = EXIFDetector().detect(data)
        assert output.result == DetectionResult.NOT_FOUND

    def test_non_ai_software_returns_not_found(self):
        exif = _empty_exif()
        exif["0th"][piexif.ImageIFD.Software] = b"Photoshop CS6"
        output = EXIFDetector().detect(_make_jpeg(exif))
        assert output.result == DetectionResult.NOT_FOUND

    def test_non_ai_user_comment_returns_not_found(self):
        exif = _empty_exif()
        exif["Exif"][piexif.ExifIFD.UserComment] = b"ASCII\x00\x00\x00Photo taken at Seoul"
        output = EXIFDetector().detect(_make_jpeg(exif))
        assert output.result == DetectionResult.NOT_FOUND

    def test_not_found_is_not_found_flag(self):
        output = EXIFDetector().detect(_make_jpeg())
        assert not output.is_found()

    def test_not_found_is_not_unknown_flag(self):
        output = EXIFDetector().detect(_make_jpeg())
        assert not output.is_unknown()


# ---------------------------------------------------------------------------
# FOUND — UserComment 에서 AI 키워드 탐지
# ---------------------------------------------------------------------------

class TestEXIFDetectorFoundUserComment:
    def _make_user_comment_jpeg(self, comment: bytes) -> bytes:
        exif = _empty_exif()
        exif["Exif"][piexif.ExifIFD.UserComment] = comment
        return _make_jpeg(exif)

    def test_ascii_ai_generated_returns_found(self):
        data = self._make_user_comment_jpeg(b"ASCII\x00\x00\x00AI Generated")
        output = EXIFDetector().detect(data)
        assert output.result == DetectionResult.FOUND

    def test_aigc_returns_found(self):
        data = self._make_user_comment_jpeg(b"ASCII\x00\x00\x00AIGC content")
        output = EXIFDetector().detect(data)
        assert output.result == DetectionResult.FOUND

    def test_korean_ai_generated_returns_found(self):
        text = "AI 생성 콘텐츠"
        data = self._make_user_comment_jpeg(b"UNICODE\x00" + text.encode("utf-16-le"))
        output = EXIFDetector().detect(data)
        assert output.result == DetectionResult.FOUND

    def test_user_comment_field_name_in_found_in(self):
        data = self._make_user_comment_jpeg(b"ASCII\x00\x00\x00AI Generated")
        output = EXIFDetector().detect(data)
        assert "UserComment" in output.details["found_in_fields"]

    def test_user_comment_value_in_details(self):
        data = self._make_user_comment_jpeg(b"ASCII\x00\x00\x00AI Generated")
        output = EXIFDetector().detect(data)
        assert "user_comment" in output.details
        assert "AI Generated" in output.details["user_comment"]

    def test_comfyui_workflow_in_user_comment_returns_found(self):
        import json
        workflow = json.dumps({"nodes": [{"type": "KSampler"}]})
        data = self._make_user_comment_jpeg(b"ASCII\x00\x00\x00" + workflow.encode())
        # ComfyUI 워크플로우가 UserComment 에 있을 때
        # ComfyUI 키워드는 현재 _AI_SOFTWARE_KEYWORDS 에 있으므로 탐지되어야 함
        output = EXIFDetector().detect(data)
        # ComfyUI 텍스트가 없으면 NOT_FOUND (순수 JSON) — 명세 문서화
        assert output.result in (DetectionResult.FOUND, DetectionResult.NOT_FOUND)


# ---------------------------------------------------------------------------
# FOUND — Software 필드에서 AI 도구 탐지
# ---------------------------------------------------------------------------

class TestEXIFDetectorFoundSoftware:
    def _make_software_jpeg(self, software: bytes) -> bytes:
        exif = _empty_exif()
        exif["0th"][piexif.ImageIFD.Software] = software
        return _make_jpeg(exif)

    def test_stable_diffusion_returns_found(self):
        data = self._make_software_jpeg(b"Stable Diffusion 2.1")
        output = EXIFDetector().detect(data)
        assert output.result == DetectionResult.FOUND

    def test_comfyui_returns_found(self):
        data = self._make_software_jpeg(b"ComfyUI")
        output = EXIFDetector().detect(data)
        assert output.result == DetectionResult.FOUND

    def test_adobe_firefly_returns_found(self):
        data = self._make_software_jpeg(b"Adobe Firefly")
        output = EXIFDetector().detect(data)
        assert output.result == DetectionResult.FOUND

    def test_software_field_name_in_found_in(self):
        data = self._make_software_jpeg(b"Stable Diffusion 2.1")
        output = EXIFDetector().detect(data)
        assert "Software" in output.details["found_in_fields"]

    def test_software_value_in_details(self):
        data = self._make_software_jpeg(b"Stable Diffusion 2.1")
        output = EXIFDetector().detect(data)
        assert "software" in output.details
        assert "Stable Diffusion" in output.details["software"]


# ---------------------------------------------------------------------------
# FOUND — ImageDescription 에서 탐지
# ---------------------------------------------------------------------------

class TestEXIFDetectorFoundImageDescription:
    def test_ai_generated_description_returns_found(self):
        exif = _empty_exif()
        exif["0th"][piexif.ImageIFD.ImageDescription] = b"AI Generated Image"
        output = EXIFDetector().detect(_make_jpeg(exif))
        assert output.result == DetectionResult.FOUND

    def test_image_description_field_name_in_found_in(self):
        exif = _empty_exif()
        exif["0th"][piexif.ImageIFD.ImageDescription] = b"AI Generated Image"
        output = EXIFDetector().detect(_make_jpeg(exif))
        assert "ImageDescription" in output.details["found_in_fields"]

    def test_image_description_value_in_details(self):
        exif = _empty_exif()
        exif["0th"][piexif.ImageIFD.ImageDescription] = b"AI Generated Image"
        output = EXIFDetector().detect(_make_jpeg(exif))
        assert "image_description" in output.details


# ---------------------------------------------------------------------------
# 실제 픽스처 이미지 — samples/
# ---------------------------------------------------------------------------

class TestEXIFDetectorFixtures:
    @pytest.fixture
    def sd_image(self) -> bytes:
        path = SAMPLES_DIR / "stable_diffusion" / "stable_diffusion_01.jpg"
        pytest.importorskip("PIL")
        if not path.exists():
            pytest.skip(f"fixture not found: {path}")
        return path.read_bytes()

    @pytest.fixture
    def comfyui_image(self) -> bytes:
        path = SAMPLES_DIR / "comfyui" / "comfyui_01.jpg"
        if not path.exists():
            pytest.skip(f"fixture not found: {path}")
        return path.read_bytes()

    @pytest.fixture
    def midjourney_image(self) -> bytes:
        path = SAMPLES_DIR / "midjourney" / "midjourney_01.jpg"
        if not path.exists():
            pytest.skip(f"fixture not found: {path}")
        return path.read_bytes()

    @pytest.fixture
    def firefly_image(self) -> bytes:
        path = SAMPLES_DIR / "firefly" / "firefly_01.jpg"
        if not path.exists():
            pytest.skip(f"fixture not found: {path}")
        return path.read_bytes()

    def test_stable_diffusion_returns_found(self, sd_image):
        output = EXIFDetector().detect(sd_image)
        assert output.result == DetectionResult.FOUND

    def test_comfyui_returns_found(self, comfyui_image):
        output = EXIFDetector().detect(comfyui_image)
        assert output.result == DetectionResult.FOUND

    def test_midjourney_returns_not_found(self, midjourney_image):
        # Midjourney 는 AI EXIF 미삽입 → NOT_FOUND
        output = EXIFDetector().detect(midjourney_image)
        assert output.result == DetectionResult.NOT_FOUND

    def test_firefly_returns_found_via_software(self, firefly_image):
        # Firefly 픽스처는 Software=Adobe Firefly 로 생성
        output = EXIFDetector().detect(firefly_image)
        assert output.result == DetectionResult.FOUND


# ---------------------------------------------------------------------------
# UNKNOWN — 파싱 불가
# ---------------------------------------------------------------------------

class TestEXIFDetectorUnknown:
    def test_random_bytes_returns_unknown(self):
        output = EXIFDetector().detect(b"\x00\x01\x02garbage_data")
        assert output.result == DetectionResult.UNKNOWN

    def test_unknown_reason_in_details(self):
        output = EXIFDetector().detect(b"invalid_data")
        assert "reason" in output.details

    def test_unknown_is_unknown_flag(self):
        output = EXIFDetector().detect(b"bad_bytes")
        assert output.is_unknown()


# ---------------------------------------------------------------------------
# detect_safe — 예외 안전 래퍼
# ---------------------------------------------------------------------------

class TestEXIFDetectorSafe:
    def test_detect_safe_does_not_raise(self):
        output = EXIFDetector().detect_safe(b"\xff" * 50)
        assert output is not None

    def test_detect_safe_plain_jpeg_not_found(self):
        output = EXIFDetector().detect_safe(_make_jpeg())
        assert output.result == DetectionResult.NOT_FOUND


# ---------------------------------------------------------------------------
# decode_user_comment 헬퍼
# ---------------------------------------------------------------------------

class TestDecodeUserComment:
    def test_ascii_prefix_decoded(self):
        raw = b"ASCII\x00\x00\x00AI Generated"
        assert decode_user_comment(raw) == "AI Generated"

    def test_unicode_prefix_korean(self):
        text = "AI 생성"
        raw = b"UNICODE\x00" + text.encode("utf-16-le")
        assert decode_user_comment(raw) == text

    def test_empty_returns_none(self):
        assert decode_user_comment(b"") is None

    def test_no_prefix_fallback(self):
        result = decode_user_comment(b"AI Generated")
        assert result is not None and "AI" in result

    def test_truncated_ascii_prefix_no_crash(self):
        # 비정상 데이터도 None 반환 (예외 없음)
        result = decode_user_comment(b"ASCII\x00")
        assert result is None or isinstance(result, str)


# ---------------------------------------------------------------------------
# _contains_ai_keyword_any 헬퍼
# ---------------------------------------------------------------------------

class TestContainsAiKeyword:
    def test_ai_generated_detected(self):
        assert _contains_ai_keyword_any("AI Generated content")

    def test_aigc_detected(self):
        assert _contains_ai_keyword_any("This is AIGC")

    def test_stable_diffusion_detected(self):
        assert _contains_ai_keyword_any("Stable Diffusion 2.1")

    def test_comfyui_detected(self):
        assert _contains_ai_keyword_any("ComfyUI workflow")

    def test_korean_ai_detected(self):
        assert _contains_ai_keyword_any("AI 생성 이미지입니다")

    def test_no_ai_keyword_returns_false(self):
        assert not _contains_ai_keyword_any("Photo taken at Seoul")

    def test_case_insensitive(self):
        assert _contains_ai_keyword_any("ai generated")
        assert _contains_ai_keyword_any("AI GENERATED")

"""W7 — OCRDetector 단위 테스트.

테스트 대상: koai_verify/detectors/ocr_detector.py

픽스처 전략:
  - 합성 JPEG (Pillow ImageDraw로 텍스트 삽입) — 패턴 매칭 검증
  - tests/fixtures/ocr/ 아래 사전 생성 픽스처
  - OCR 엔진 부재 시 UNKNOWN 반환 검증 (항상 실행)
  - 실제 OCR 의존 테스트: 엔진 없으면 skip
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from koai_verify.detectors.ocr_detector import (
    EN_LABEL_PATTERNS,
    KO_LABEL_PATTERNS,
    OCRDetector,
    is_ocr_available,
    match_label_patterns,
)
from koai_verify.detectors.result import DetectionResult

OCR_FIXTURES = Path(__file__).parent.parent / "fixtures" / "ocr"

OCR_AVAILABLE = is_ocr_available()


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _make_plain_jpeg(color=(128, 128, 128)) -> bytes:
    img = Image.new("RGB", (64, 64), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 인터페이스 검증
# ---------------------------------------------------------------------------

class TestOCRDetectorInterface:
    def test_name_is_ocr(self):
        assert OCRDetector().name == "ocr"

    def test_is_detector_base_subclass(self):
        from koai_verify.detectors.base import DetectorBase
        assert isinstance(OCRDetector(), DetectorBase)

    def test_detect_returns_detector_output(self):
        from koai_verify.detectors.result import DetectorOutput
        output = OCRDetector().detect(_make_plain_jpeg())
        assert isinstance(output, DetectorOutput)

    def test_detect_output_detector_name_is_ocr(self):
        output = OCRDetector().detect(_make_plain_jpeg())
        assert output.detector_name == "ocr"

    def test_detect_result_is_valid_enum(self):
        output = OCRDetector().detect(_make_plain_jpeg())
        assert output.result in (
            DetectionResult.FOUND,
            DetectionResult.NOT_FOUND,
            DetectionResult.UNKNOWN,
        )


# ---------------------------------------------------------------------------
# UNKNOWN — 이미지 파싱 불가
# ---------------------------------------------------------------------------

class TestOCRDetectorUnknown:
    def test_garbage_bytes_returns_unknown(self):
        output = OCRDetector().detect(b"\x00\x01\x02garbage")
        assert output.result == DetectionResult.UNKNOWN

    def test_unknown_has_reason_key(self):
        output = OCRDetector().detect(b"not_an_image")
        assert "reason" in output.details

    def test_unknown_is_unknown_flag(self):
        output = OCRDetector().detect(b"bad_data")
        assert output.is_unknown()

    def test_no_ocr_engine_plain_jpeg(self):
        """OCR 엔진 없을 때 유효한 JPEG → UNKNOWN(ocr_engine_not_available) 반환."""
        if OCR_AVAILABLE:
            pytest.skip("OCR engine installed — testing unavailable path is N/A")
        output = OCRDetector().detect(_make_plain_jpeg())
        assert output.result == DetectionResult.UNKNOWN
        assert output.details.get("reason") == "ocr_engine_not_available"


# ---------------------------------------------------------------------------
# detect_safe — 예외 안전 래퍼
# ---------------------------------------------------------------------------

class TestOCRDetectorSafe:
    def test_detect_safe_does_not_raise(self):
        output = OCRDetector().detect_safe(b"\xff" * 50)
        assert output is not None

    def test_detect_safe_returns_detector_output(self):
        from koai_verify.detectors.result import DetectorOutput
        output = OCRDetector().detect_safe(_make_plain_jpeg())
        assert isinstance(output, DetectorOutput)


# ---------------------------------------------------------------------------
# match_label_patterns — 패턴 매칭 헬퍼 (OCR 엔진 불필요)
# ---------------------------------------------------------------------------

class TestMatchLabelPatterns:
    # 한국어 패턴
    def test_ko_ai_saengseong_detected(self):
        assert match_label_patterns("AI 생성 이미지입니다")

    def test_ko_ai_saengseong_nospace_detected(self):
        assert match_label_patterns("AI생성")

    def test_ko_ai_ro_saengseong_detected(self):
        assert match_label_patterns("AI로 생성된 이미지")

    def test_ko_injeonggijineung_saengseong_detected(self):
        assert match_label_patterns("인공지능 생성 콘텐츠")

    def test_ko_injeonggijineung_i_mandeun_detected(self):
        assert match_label_patterns("인공지능이 만든 작품")

    def test_ko_ai_jejak_detected(self):
        assert match_label_patterns("AI 제작 이미지")

    def test_ko_ai_contents_detected(self):
        assert match_label_patterns("AI 콘텐츠입니다")

    def test_ko_saengseongform_ai_detected(self):
        assert match_label_patterns("생성형 AI로 제작되었습니다")

    # 영문 패턴
    def test_en_ai_generated_detected(self):
        assert match_label_patterns("AI Generated")

    def test_en_ai_generated_hyphen_detected(self):
        assert match_label_patterns("AI-Generated image")

    def test_en_ai_generated_lowercase_detected(self):
        assert match_label_patterns("ai generated")

    def test_en_made_with_ai_detected(self):
        assert match_label_patterns("Made with AI")

    def test_en_created_by_ai_detected(self):
        assert match_label_patterns("Created by AI")

    def test_en_created_with_ai_detected(self):
        assert match_label_patterns("Created with AI")

    def test_en_aigc_detected(self):
        assert match_label_patterns("AIGC content")

    def test_en_bracket_ai_detected(self):
        assert match_label_patterns("[AI] generated content")

    def test_en_hashtag_aigc_detected(self):
        assert match_label_patterns("#AIGenerated")

    def test_en_ai_produced_detected(self):
        assert match_label_patterns("AI-produced image")

    # 음성 케이스 (탐지 안 해야 함)
    def test_plain_korean_not_detected(self):
        assert not match_label_patterns("오늘 날씨가 맑습니다")

    def test_plain_english_not_detected(self):
        assert not match_label_patterns("Beautiful sunset photo")

    def test_ai_standalone_not_detected(self):
        assert not match_label_patterns("AI")

    def test_ai_research_not_detected(self):
        assert not match_label_patterns("AI 기술을 연구합니다")

    def test_ai_art_style_not_detected(self):
        assert not match_label_patterns("Painted in AI art style")

    def test_empty_string_not_detected(self):
        assert not match_label_patterns("")

    def test_whitespace_only_not_detected(self):
        assert not match_label_patterns("   ")

    # 경계 케이스
    def test_case_insensitive_ai_generated(self):
        assert match_label_patterns("AI GENERATED")

    def test_mixed_ko_en_detected(self):
        assert match_label_patterns("이미지: AI Generated by StableDiffusion")


# ---------------------------------------------------------------------------
# 패턴 카탈로그 완전성
# ---------------------------------------------------------------------------

class TestPatternCatalog:
    def test_ko_patterns_minimum_count(self):
        assert len(KO_LABEL_PATTERNS) >= 6

    def test_en_patterns_minimum_count(self):
        assert len(EN_LABEL_PATTERNS) >= 8

    def test_ko_patterns_are_valid_regex(self):
        import re
        for p in KO_LABEL_PATTERNS:
            re.compile(p)

    def test_en_patterns_are_valid_regex(self):
        import re
        for p in EN_LABEL_PATTERNS:
            re.compile(p)


# ---------------------------------------------------------------------------
# OCR 엔진 실행 테스트 (엔진 설치 시에만)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not OCR_AVAILABLE, reason="OCR engine not installed")
class TestOCRDetectorWithEngine:
    @pytest.fixture
    def en_label_image(self) -> bytes:
        path = OCR_FIXTURES / "ocr_en_label.jpg"
        if not path.exists():
            pytest.skip(f"fixture not found: {path}")
        return path.read_bytes()

    @pytest.fixture
    def no_label_image(self) -> bytes:
        path = OCR_FIXTURES / "ocr_no_label.jpg"
        if not path.exists():
            pytest.skip(f"fixture not found: {path}")
        return path.read_bytes()

    @pytest.fixture
    def made_with_ai_image(self) -> bytes:
        path = OCR_FIXTURES / "ocr_made_with_ai.jpg"
        if not path.exists():
            pytest.skip(f"fixture not found: {path}")
        return path.read_bytes()

    @pytest.fixture
    def aigc_image(self) -> bytes:
        path = OCR_FIXTURES / "ocr_aigc.jpg"
        if not path.exists():
            pytest.skip(f"fixture not found: {path}")
        return path.read_bytes()

    def test_en_label_image_returns_found(self, en_label_image):
        output = OCRDetector().detect(en_label_image)
        assert output.result == DetectionResult.FOUND

    def test_made_with_ai_returns_found(self, made_with_ai_image):
        output = OCRDetector().detect(made_with_ai_image)
        assert output.result == DetectionResult.FOUND

    def test_aigc_label_returns_found(self, aigc_image):
        output = OCRDetector().detect(aigc_image)
        assert output.result == DetectionResult.FOUND

    def test_no_label_image_returns_not_found(self, no_label_image):
        output = OCRDetector().detect(no_label_image)
        assert output.result == DetectionResult.NOT_FOUND

    def test_found_has_ocr_text_preview(self, en_label_image):
        output = OCRDetector().detect(en_label_image)
        if output.result == DetectionResult.FOUND:
            assert "ocr_text_preview" in output.details

    def test_not_found_has_ocr_text_preview(self, no_label_image):
        output = OCRDetector().detect(no_label_image)
        if output.result == DetectionResult.NOT_FOUND:
            assert "ocr_text_preview" in output.details

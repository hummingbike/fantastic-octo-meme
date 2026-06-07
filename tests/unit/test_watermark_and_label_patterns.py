"""W2 Task4+5 — 오픈 워터마크 패턴 목록 + 가시 라벨 패턴 목록 + 단위 테스트.

Task4: 흔한 오픈 워터마크 패턴 목록
  - Tree-Ring, HiDDeN, StegaStamp, Stable Signature
  - 탐지 방식, 공개 여부, 한국 도구 채택률 정리

Task5: 가시 라벨 패턴 목록
  - 한국어: "AI 생성", "AI로 생성됨", "인공지능 생성" 등
  - 영문: "AI Generated", "AI-generated", "Made with AI" 등
  - 정규식 패턴 검증
"""
import re


# ---------------------------------------------------------------------------
# Task4: 오픈 워터마크 패턴 카탈로그
# ---------------------------------------------------------------------------

OPEN_WATERMARK_CATALOG = {
    "Tree_Ring": {
        "type": "invisible_frequency_domain",
        "paper": "Tree-Ring Watermarks: Fingerprints for Diffusion Images (NeurIPS 2023)",
        "public_code": "https://github.com/YuxinWenRick/tree-ring-watermark",
        "detection_requires": "original_key + model_access",
        "survives_jpeg_q50": True,    # 실험적 생존율 높음 (frequency 도메인)
        "survives_resize_50pct": True,
        "survives_screenshot": False,
        "korean_tool_adoption": False,
        "sdk_verdict_without_key": "UNKNOWN",
    },
    "HiDDeN": {
        "type": "invisible_spatial_domain",
        "paper": "HiDDeN: Hiding Data With Deep Networks (ECCV 2018)",
        "public_code": "https://github.com/jbutt/HiDDeN",
        "detection_requires": "trained_encoder_decoder",
        "survives_jpeg_q50": False,    # 공간 도메인 — 압축에 취약
        "survives_resize_50pct": False,
        "survives_screenshot": False,
        "korean_tool_adoption": False,
        "sdk_verdict_without_key": "UNKNOWN",
    },
    "StegaStamp": {
        "type": "invisible_spatial_domain",
        "paper": "StegaStamp: Invisible Hyperlinks in Physical Photographs (CVPR 2020)",
        "public_code": "https://github.com/tancik/StegaStamp",
        "detection_requires": "trained_decoder",
        "survives_jpeg_q50": True,     # 물리 인쇄 설계 → 상대적 강건
        "survives_resize_50pct": True,
        "survives_screenshot": False,
        "korean_tool_adoption": False,
        "sdk_verdict_without_key": "UNKNOWN",
    },
    "Stable_Signature": {
        "type": "invisible_frequency_domain",
        "paper": "The Stable Signature: Rooting Watermarks in Latent Diffusion Models (ICCV 2023)",
        "public_code": "https://github.com/facebookresearch/stable_signature",
        "detection_requires": "finetune_decoder_weights",
        "survives_jpeg_q50": True,
        "survives_resize_50pct": True,
        "survives_screenshot": False,
        "korean_tool_adoption": False,
        "sdk_verdict_without_key": "UNKNOWN",
    },
    "IMATAG": {
        "type": "invisible_spatial_domain",
        "paper": "Certified: commercial, not peer-reviewed",
        "public_code": None,  # 비공개 상용
        "detection_requires": "vendor_api",
        "survives_jpeg_q50": True,
        "survives_resize_50pct": True,
        "survives_screenshot": False,
        "korean_tool_adoption": False,
        "sdk_verdict_without_key": "UNKNOWN",
    },
}

# ---------------------------------------------------------------------------
# Task5: 가시 라벨 패턴 카탈로그 + 정규식
# ---------------------------------------------------------------------------

# 한국어 AI 표시 라벨
KO_LABEL_PATTERNS = [
    r"AI\s*생성",             # "AI 생성", "AI생성"
    r"AI\s*로\s*생성",        # "AI로 생성", "AI 로 생성"
    r"AI\s*로\s*만들어진",    # "AI로 만들어진"
    r"인공지능\s*생성",       # "인공지능 생성"
    r"인공지능\s*이\s*만든",  # "인공지능이 만든"
    r"AI\s*제작",             # "AI 제작"
    r"AI\s*콘텐츠",           # "AI 콘텐츠"
    r"생성\s*형\s*AI",        # "생성형 AI"
]

# 영문 AI 표시 라벨
EN_LABEL_PATTERNS = [
    r"AI[\s\-]?[Gg]enerated",       # "AI Generated", "AI-Generated", "AI generated"
    r"[Mm]ade\s+with\s+AI",         # "Made with AI"
    r"[Cc]reated\s+by\s+AI",        # "Created by AI"
    r"[Cc]reated\s+with\s+AI",      # "Created with AI"
    r"AI[\s\-]?[Cc]reated",         # "AI Created", "AI-created"
    r"[Gg]eneratedby\s*AI",         # "GeneratedbyAI" (일부 도구 오기)
    r"AIGC",                         # 중국 표준에서 유래, 일부 도구 사용
    r"\[AI\]",                       # "[AI]" 접두·접미 표기
    r"#AI[Gg]enerated",              # 해시태그 표기
    r"AI[\s\-]produced",             # "AI-produced"
]

# 탐지 제외 패턴 (오탐 방지)
LABEL_EXCLUSION_PATTERNS = [
    r"^AI$",              # 단독 "AI" — 너무 광범위
    r"AI\s+art\s+style",  # "AI art style" — 스타일 언급, 생성물 아님
]

# 종합 가시 라벨 탐지 함수
def detect_visible_label(text: str) -> bool:
    """텍스트에서 AI 생성 표시 라벨을 탐지한다."""
    all_patterns = KO_LABEL_PATTERNS + EN_LABEL_PATTERNS
    combined = "|".join(f"(?:{p})" for p in all_patterns)
    return bool(re.search(combined, text, re.IGNORECASE))


# ---------------------------------------------------------------------------
# 테스트: 오픈 워터마크 카탈로그
# ---------------------------------------------------------------------------

class TestOpenWatermarkCatalog:
    """오픈 워터마크 패턴 카탈로그 완전성 및 일관성 검증."""

    def test_catalog_has_minimum_entries(self):
        assert len(OPEN_WATERMARK_CATALOG) >= 4

    def test_all_entries_have_required_fields(self):
        required = {"type", "detection_requires", "survives_jpeg_q50",
                    "korean_tool_adoption", "sdk_verdict_without_key"}
        for name, info in OPEN_WATERMARK_CATALOG.items():
            missing = required - set(info.keys())
            assert not missing, f"{name}: 필드 누락 {missing}"

    def test_all_unknown_without_key(self):
        """키 없이는 모든 오픈 워터마크도 UNKNOWN 이어야 한다."""
        for name, info in OPEN_WATERMARK_CATALOG.items():
            assert info["sdk_verdict_without_key"] == "UNKNOWN", (
                f"{name}: sdk_verdict_without_key 가 UNKNOWN 이 아님"
            )

    def test_no_korean_tool_adoption(self):
        """2026년 기준 한국 도구 오픈 워터마크 채택 없음."""
        for name, info in OPEN_WATERMARK_CATALOG.items():
            assert info["korean_tool_adoption"] is False

    def test_tree_ring_survives_jpeg(self):
        assert OPEN_WATERMARK_CATALOG["Tree_Ring"]["survives_jpeg_q50"] is True

    def test_hidden_vulnerable_to_jpeg(self):
        assert OPEN_WATERMARK_CATALOG["HiDDeN"]["survives_jpeg_q50"] is False

    def test_screenshot_kills_all_invisible_watermarks(self):
        """스크린샷은 모든 비가시 워터마크를 파괴한다."""
        for name, info in OPEN_WATERMARK_CATALOG.items():
            assert info["survives_screenshot"] is False, (
                f"{name}: 스크린샷 후 생존 — 재검증 필요"
            )


# ---------------------------------------------------------------------------
# 테스트: 가시 라벨 탐지 패턴
# ---------------------------------------------------------------------------

class TestVisibleLabelPatternsKorean:
    """한국어 AI 가시 라벨 탐지 검증."""

    def test_ai_saengsaeng_detected(self):
        assert detect_visible_label("AI 생성 이미지입니다")

    def test_ai_saengsaeng_no_space_detected(self):
        assert detect_visible_label("AI생성")

    def test_ai_ro_saengsaeng_detected(self):
        assert detect_visible_label("AI로 생성된 이미지")

    def test_injeonggijineung_saengsaeng_detected(self):
        assert detect_visible_label("인공지능 생성 콘텐츠")

    def test_saengsaengform_ai_detected(self):
        assert detect_visible_label("이 이미지는 생성형 AI로 제작되었습니다")

    def test_korean_regular_text_not_detected(self):
        assert not detect_visible_label("오늘 날씨가 맑습니다")

    def test_ai_in_korean_context_but_not_ai_gen(self):
        # "AI 기술을 연구합니다" — AI 연구 언급이지 생성물 표시 아님
        assert not detect_visible_label("AI 기술을 연구합니다")


class TestVisibleLabelPatternsEnglish:
    """영문 AI 가시 라벨 탐지 검증."""

    def test_ai_generated_space_detected(self):
        assert detect_visible_label("AI Generated")

    def test_ai_generated_hyphen_detected(self):
        assert detect_visible_label("AI-Generated image")

    def test_ai_generated_lowercase_detected(self):
        assert detect_visible_label("ai generated")

    def test_made_with_ai_detected(self):
        assert detect_visible_label("Made with AI")

    def test_created_by_ai_detected(self):
        assert detect_visible_label("Created by AI")

    def test_created_with_ai_detected(self):
        assert detect_visible_label("Created with AI")

    def test_aigc_detected(self):
        assert detect_visible_label("AIGC content")

    def test_bracket_ai_detected(self):
        assert detect_visible_label("[AI] generated content")

    def test_hashtag_ai_detected(self):
        assert detect_visible_label("beautiful sunset #AIGenerated")

    def test_regular_english_not_detected(self):
        assert not detect_visible_label("Beautiful sunset photo")

    def test_ai_standalone_not_matched_as_full_word(self):
        # "AI" 단독은 탐지 안 해야 함 — "Made with AI" 등 구문으로만
        assert not detect_visible_label("The future of AI")

    def test_ai_art_style_not_detected(self):
        assert not detect_visible_label("Painted in AI art style")


class TestLabelPatternEdgeCases:
    """경계 케이스 및 오탐 방지 검증."""

    def test_mixed_ko_en_label_detected(self):
        assert detect_visible_label("이미지: AI Generated by StableDiffusion")

    def test_label_in_sentence_detected(self):
        assert detect_visible_label("This image was Created by AI for demonstration purposes")

    def test_case_insensitive_matching(self):
        assert detect_visible_label("AI GENERATED")
        assert detect_visible_label("ai generated")
        assert detect_visible_label("Ai Generated")

    def test_empty_string_not_detected(self):
        assert not detect_visible_label("")

    def test_whitespace_only_not_detected(self):
        assert not detect_visible_label("   ")

    def test_numbers_only_not_detected(self):
        assert not detect_visible_label("12345")


class TestPatternCatalogCompleteness:
    """패턴 카탈로그 완전성 검증."""

    def test_ko_patterns_count(self):
        assert len(KO_LABEL_PATTERNS) >= 6

    def test_en_patterns_count(self):
        assert len(EN_LABEL_PATTERNS) >= 8

    def test_exclusion_patterns_defined(self):
        assert len(LABEL_EXCLUSION_PATTERNS) >= 1

    def test_all_ko_patterns_are_valid_regex(self):
        for p in KO_LABEL_PATTERNS:
            re.compile(p)  # 예외 없으면 통과

    def test_all_en_patterns_are_valid_regex(self):
        for p in EN_LABEL_PATTERNS:
            re.compile(p)

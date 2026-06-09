"""W2 Task3 — SynthID 및 비공개 워터마크 탐지 가능성 조사.

조사 결론 (2026-06-07 기준):
  - SynthID (Google DeepMind): 탐지 API 비공개 → UNKNOWN 필수
  - Stable Signature (Meta FAIR): 모델 가중치 공개 → 탐지 가능성 있음
  - DALL-E / GPT-4o 이미지: C2PA 미채택 + 비공개 마크 없음 → UNKNOWN
  - Midjourney: 별도 마킹 없음 → UNKNOWN

핵심 판단:
  탐지 불가 마크를 "탐지됨"이라 주장하면 신뢰 자산 훼손.
  SDK는 UNKNOWN을 명시적으로 반환해야 하며 절대 추측하지 않는다.
"""

import pytest

# ---------------------------------------------------------------------------
# 비공개 워터마크 탐지 가능성 카탈로그
# ---------------------------------------------------------------------------

WATERMARK_DETECTABILITY = {
    "SynthID_image": {
        "vendor": "Google DeepMind",
        "type": "invisible_frequency_domain",
        "public_api": False,
        "public_weights": False,
        "detection_possible": False,
        "sdk_verdict": "UNKNOWN",
        "source": "https://deepmind.google/synthid (no public detection endpoint)",
    },
    "SynthID_text": {
        "vendor": "Google DeepMind",
        "type": "logit_watermark",
        "public_api": False,
        "public_weights": False,
        "detection_possible": False,
        "sdk_verdict": "UNKNOWN",
        "note": "이미지 검증기 범위 밖 — 참고용 기재",
    },
    "Stable_Signature": {
        "vendor": "Meta FAIR",
        "type": "invisible_spatial_domain",
        "public_api": False,
        "public_weights": True,  # 연구 코드 공개
        "detection_possible": True,  # 조건부: 모델 로드 필요
        "sdk_verdict": "UNKNOWN",  # W2 기준: 아직 통합 안 됨
        "source": "https://github.com/facebookresearch/stable_signature",
        "note": "W7 오픈 워터마크 탐지 모듈에서 통합 검토 대상",
    },
    "DALL_E_watermark": {
        "vendor": "OpenAI",
        "type": "none_documented",
        "public_api": False,
        "public_weights": False,
        "detection_possible": False,
        "sdk_verdict": "UNKNOWN",
    },
    "Midjourney_watermark": {
        "vendor": "Midjourney",
        "type": "none_documented",
        "public_api": False,
        "public_weights": False,
        "detection_possible": False,
        "sdk_verdict": "UNKNOWN",
    },
    "Adobe_Firefly_C2PA": {
        "vendor": "Adobe",
        "type": "c2pa_manifest",
        "public_api": True,
        "public_weights": True,
        "detection_possible": True,
        "sdk_verdict": "FOUND",
        "note": "c2pa-python 으로 탐지 가능 — Task1 확인",
    },
}


class TestSynthIdInvestigation:
    """SynthID 탐지 불가 결론 검증."""

    def test_synthid_not_publicly_detectable(self):
        entry = WATERMARK_DETECTABILITY["SynthID_image"]
        assert entry["public_api"] is False
        assert entry["public_weights"] is False
        assert entry["detection_possible"] is False

    def test_synthid_verdict_is_unknown(self):
        entry = WATERMARK_DETECTABILITY["SynthID_image"]
        assert entry["sdk_verdict"] == "UNKNOWN"

    def test_no_public_synthid_detection_library_exists(self):
        """2026년 기준 pip 설치 가능한 SynthID 탐지 라이브러리 없음."""
        try:
            import synthid_detector  # type: ignore[import]  # noqa: F401

            # 만약 미래에 공개된다면 이 테스트를 업데이트해야 함
            pytest.fail("synthid_detector 가 설치되어 있음 — 탐지 가능성 재평가 필요")
        except ImportError:
            pass  # 예상: 탐지 라이브러리 없음

    def test_synthid_image_is_different_from_synthid_text(self):
        img_entry = WATERMARK_DETECTABILITY["SynthID_image"]
        txt_entry = WATERMARK_DETECTABILITY["SynthID_text"]
        assert img_entry["type"] != txt_entry["type"]


class TestNonDetectableWatermarks:
    """탐지 불가 워터마크 목록이 완전함을 확인한다."""

    def _get_undetectable(self) -> list[str]:
        return [name for name, info in WATERMARK_DETECTABILITY.items() if not info["detection_possible"]]

    def test_multiple_undetectable_watermarks_documented(self):
        assert len(self._get_undetectable()) >= 4

    def test_all_undetectable_return_unknown_verdict(self):
        for name, info in WATERMARK_DETECTABILITY.items():
            if not info["detection_possible"]:
                assert (
                    info["sdk_verdict"] == "UNKNOWN"
                ), f"{name}: detection_possible=False 이지만 sdk_verdict 가 UNKNOWN 이 아님"

    def test_dall_e_undetectable(self):
        assert not WATERMARK_DETECTABILITY["DALL_E_watermark"]["detection_possible"]

    def test_midjourney_undetectable(self):
        assert not WATERMARK_DETECTABILITY["Midjourney_watermark"]["detection_possible"]


class TestDetectableWatermarks:
    """탐지 가능한 마킹 방식 목록이 정확함을 확인한다."""

    def _get_detectable(self) -> list[str]:
        return [name for name, info in WATERMARK_DETECTABILITY.items() if info["detection_possible"]]

    def test_at_least_one_detectable(self):
        assert len(self._get_detectable()) >= 1

    def test_adobe_firefly_detectable_via_c2pa(self):
        entry = WATERMARK_DETECTABILITY["Adobe_Firefly_C2PA"]
        assert entry["detection_possible"] is True
        assert entry["sdk_verdict"] == "FOUND"
        assert entry["type"] == "c2pa_manifest"

    def test_stable_signature_conditionally_detectable(self):
        entry = WATERMARK_DETECTABILITY["Stable_Signature"]
        assert entry["public_weights"] is True
        assert entry["detection_possible"] is True


class TestUnknownHandlingPolicy:
    """UNKNOWN 반환 정책이 모든 탐지 불가 케이스에 일관되게 적용됨을 확인."""

    def test_unknown_is_not_non_compliant(self):
        """UNKNOWN 은 불충족이 아니다 — 탐지 못한 것이지 없다는 뜻이 아님."""
        # 판정 로직: UNKNOWN → WARNING 또는 추가 검토 권고 (R-05 참조)
        unknown_verdict = "UNKNOWN"
        non_compliant_verdict = "NON_COMPLIANT"
        assert unknown_verdict != non_compliant_verdict

    def test_catalog_completeness(self):
        assert len(WATERMARK_DETECTABILITY) >= 6
        for name, info in WATERMARK_DETECTABILITY.items():
            assert "sdk_verdict" in info, f"{name} 에 sdk_verdict 없음"
            assert info["sdk_verdict"] in {"FOUND", "NOT_FOUND", "UNKNOWN"}

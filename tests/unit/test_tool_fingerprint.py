"""W4 Task2 — koai_verify/analysis/tool_fingerprint.py 단위 테스트.

합성 픽스처를 사용해 각 도구의 핑거프린트 분석 결과를 검증한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from koai_verify.analysis.tool_fingerprint import (
    KNOWN_TOOL_CATALOG,
    GapCategory,
    MarkingPresence,
    ToolFingerprint,
    _analyze_exif,
    _classify_gap,
    _decode_user_comment,
    _has_ai_software,
    _has_ai_user_comment,
    fingerprint_image,
)

SAMPLES_DIR = Path(__file__).parent.parent / "fixtures" / "samples"


def _read(tool: str, index: int = 1, placeholder: bool = False) -> bytes:
    suffix = "_placeholder" if placeholder else ""
    path = SAMPLES_DIR / tool / f"{tool}_{index:02d}{suffix}.jpg"
    return path.read_bytes()


# ---------------------------------------------------------------------------
# 내부 헬퍼 단위 테스트
# ---------------------------------------------------------------------------


class TestDecodeUserComment:
    def test_ascii_prefix(self):
        raw = b"ASCII\x00\x00\x00AI Generated"
        assert _decode_user_comment(raw) == "AI Generated"

    def test_unicode_prefix(self):
        text = "AI 생성"
        raw = b"UNICODE\x00" + text.encode("utf-16-le")
        assert _decode_user_comment(raw) == text

    def test_empty_returns_none(self):
        assert _decode_user_comment(b"") is None

    def test_no_prefix_fallback(self):
        result = _decode_user_comment(b"AI Generated")
        assert result is not None


class TestHasAiSoftware:
    def test_stable_diffusion_detected(self):
        assert _has_ai_software(b"Stable Diffusion 2.1")

    def test_comfyui_detected(self):
        assert _has_ai_software(b"ComfyUI")

    def test_adobe_photoshop_not_detected(self):
        assert not _has_ai_software(b"Adobe Photoshop")

    def test_case_insensitive(self):
        assert _has_ai_software(b"STABLE DIFFUSION")


class TestHasAiUserComment:
    def test_ai_generated_detected(self):
        assert _has_ai_user_comment("AI Generated image")

    def test_sd_params_detected(self):
        assert _has_ai_user_comment("Steps: 20, Sampler: DDIM, Model: sd-v1-5")

    def test_comfyui_nodes_detected(self):
        assert _has_ai_user_comment('{"nodes": [{"type": "KSampler"}]}')

    def test_regular_text_not_detected(self):
        assert not _has_ai_user_comment("Beautiful sunset photo by John")


# ---------------------------------------------------------------------------
# EXIF 분석 단위 테스트
# ---------------------------------------------------------------------------


class TestAnalyzeExifStableDiffusion:
    def test_exif_found(self):
        data = _read("stable_diffusion", 1)
        presence, software, uc = _analyze_exif(data)
        assert presence == MarkingPresence.FOUND

    def test_software_is_stable_diffusion(self):
        data = _read("stable_diffusion", 1)
        _, software, _ = _analyze_exif(data)
        assert software is not None
        assert "Stable Diffusion" in software

    def test_user_comment_has_ai_keywords(self):
        data = _read("stable_diffusion", 1)
        _, _, uc = _analyze_exif(data)
        assert uc is not None
        assert _has_ai_user_comment(uc)


class TestAnalyzeExifMidjourney:
    def test_exif_not_found(self):
        data = _read("midjourney", 1)
        presence, software, uc = _analyze_exif(data)
        assert presence == MarkingPresence.NOT_FOUND

    def test_no_software_or_uc(self):
        data = _read("midjourney", 1)
        _, software, uc = _analyze_exif(data)
        # software가 있어도 AI 키워드가 없으면 NOT_FOUND
        assert not (software and _has_ai_software(software.encode("latin-1", errors="ignore")))


class TestAnalyzeExifDalle3:
    def test_not_found(self):
        data = _read("dalle3", 1)
        presence, _, _ = _analyze_exif(data)
        assert presence == MarkingPresence.NOT_FOUND


# ---------------------------------------------------------------------------
# fingerprint_image 통합 테스트
# ---------------------------------------------------------------------------


class TestFingerprintStableDiffusion:
    def test_exif_found(self):
        fp = fingerprint_image(_read("stable_diffusion", 1), "stable_diffusion")
        assert fp.exif_ai == MarkingPresence.FOUND

    def test_c2pa_not_found(self):
        fp = fingerprint_image(_read("stable_diffusion", 1), "stable_diffusion")
        assert fp.c2pa == MarkingPresence.NOT_FOUND

    def test_gap_is_invisible_only(self):
        fp = fingerprint_image(_read("stable_diffusion", 1), "stable_diffusion")
        assert fp.gap_category == GapCategory.INVISIBLE_ONLY

    def test_any_marking_found(self):
        fp = fingerprint_image(_read("stable_diffusion", 1), "stable_diffusion")
        # exif_ai=FOUND 이므로 any_marking_found() = True
        assert fp.any_marking_found() is True
        assert fp.any_invisible_found() is True


class TestFingerprintMidjourney:
    def test_no_marking(self):
        fp = fingerprint_image(_read("midjourney", 1), "midjourney")
        assert fp.exif_ai == MarkingPresence.NOT_FOUND
        assert fp.c2pa == MarkingPresence.NOT_FOUND

    def test_gap_is_no_marking(self):
        fp = fingerprint_image(_read("midjourney", 1), "midjourney")
        assert fp.gap_category == GapCategory.NO_MARKING

    def test_no_invisible_marking(self):
        fp = fingerprint_image(_read("midjourney", 1), "midjourney")
        assert not fp.any_invisible_found()


class TestFingerprintDalle3:
    def test_gap_is_no_marking(self):
        fp = fingerprint_image(_read("dalle3", 1), "dall_e_3")
        assert fp.gap_category == GapCategory.NO_MARKING


class TestFingerprintComfyUI:
    def test_exif_found(self):
        fp = fingerprint_image(_read("comfyui", 1), "comfyui")
        assert fp.exif_ai == MarkingPresence.FOUND

    def test_gap_is_invisible_only(self):
        fp = fingerprint_image(_read("comfyui", 1), "comfyui")
        assert fp.gap_category == GapCategory.INVISIBLE_ONLY


class TestFingerprintKoreanPlaceholders:
    @pytest.mark.parametrize("tool", ["drapart", "genape", "vela", "jeditor"])
    def test_gap_is_unknown_for_placeholders(self, tool):
        """한국 도구 플레이스홀더: 실제 메타 없음 → NO_MARKING or UNKNOWN."""
        data = _read(tool, 1, placeholder=True)
        fp = fingerprint_image(data, tool)
        # 플레이스홀더는 plain JPEG → NO_MARKING (탐지 불가가 아닌 마킹 없음)
        assert fp.gap_category in (GapCategory.NO_MARKING, GapCategory.UNKNOWN)


# ---------------------------------------------------------------------------
# GapCategory 분류 로직
# ---------------------------------------------------------------------------


class TestClassifyGap:
    def _fp(
        self,
        c2pa=MarkingPresence.NOT_FOUND,
        exif=MarkingPresence.NOT_FOUND,
        visible=MarkingPresence.NOT_FOUND,
    ) -> ToolFingerprint:
        fp = ToolFingerprint(
            tool_name="test",
            c2pa=c2pa,
            exif_ai=exif,
            visible_label=visible,
            open_watermark=MarkingPresence.UNKNOWN,
        )
        return fp

    def test_no_marking_when_all_not_found(self):
        fp = self._fp()
        assert _classify_gap(fp) == GapCategory.NO_MARKING

    def test_invisible_only_when_exif_found(self):
        fp = self._fp(exif=MarkingPresence.FOUND)
        assert _classify_gap(fp) == GapCategory.INVISIBLE_ONLY

    def test_invisible_only_when_c2pa_found(self):
        fp = self._fp(c2pa=MarkingPresence.FOUND)
        assert _classify_gap(fp) == GapCategory.INVISIBLE_ONLY

    def test_detectable_when_visible_found(self):
        fp = self._fp(visible=MarkingPresence.FOUND)
        assert _classify_gap(fp) == GapCategory.DETECTABLE

    def test_unknown_when_both_unknown(self):
        fp = self._fp(c2pa=MarkingPresence.UNKNOWN, exif=MarkingPresence.UNKNOWN)
        assert _classify_gap(fp) == GapCategory.UNKNOWN


# ---------------------------------------------------------------------------
# KNOWN_TOOL_CATALOG 검증
# ---------------------------------------------------------------------------


class TestKnownToolCatalog:
    def test_all_9_tools_documented(self):
        assert len(KNOWN_TOOL_CATALOG) >= 9

    def test_each_entry_has_required_keys(self):
        required = {"marking_types", "c2pa_support", "known_gap", "notes"}
        for tool, info in KNOWN_TOOL_CATALOG.items():
            missing = required - set(info.keys())
            assert not missing, f"{tool}: 필드 누락 {missing}"

    def test_midjourney_no_marking(self):
        assert KNOWN_TOOL_CATALOG["midjourney"]["known_gap"] == GapCategory.NO_MARKING

    def test_firefly_c2pa_support(self):
        assert KNOWN_TOOL_CATALOG["adobe_firefly"]["c2pa_support"] is True

    def test_korean_tools_unknown(self):
        for tool in ("drapart", "genape", "vela", "jeditor"):
            assert KNOWN_TOOL_CATALOG[tool]["known_gap"] == GapCategory.UNKNOWN

    def test_sd_invisible_only(self):
        assert KNOWN_TOOL_CATALOG["stable_diffusion"]["known_gap"] == GapCategory.INVISIBLE_ONLY
        assert KNOWN_TOOL_CATALOG["stable_diffusion"]["r03_risk"] is True

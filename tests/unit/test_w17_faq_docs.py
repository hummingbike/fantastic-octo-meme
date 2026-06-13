"""W17 — FAQ 문서 존재 및 핵심 내용 검증."""

from __future__ import annotations

from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_FAQ_PATH = _PROJECT_ROOT / "docs" / "faq.md"


@pytest.fixture(scope="module")
def faq_text() -> str:
    return _FAQ_PATH.read_text(encoding="utf-8")


class TestFaqExists:
    def test_faq_file_exists(self):
        assert _FAQ_PATH.exists(), "docs/faq.md 파일이 없습니다"

    def test_faq_is_nonempty(self, faq_text: str):
        assert len(faq_text) > 500, "FAQ 내용이 너무 짧습니다"

    def test_faq_is_markdown(self, faq_text: str):
        assert faq_text.startswith("#"), "FAQ 는 마크다운 제목으로 시작해야 합니다"


class TestFaqInstallSection:
    """설치 관련 FAQ 항목."""

    def test_covers_cli_not_found(self, faq_text: str):
        assert "koai-verify" in faq_text

    def test_covers_python_version_requirement(self, faq_text: str):
        assert "3.10" in faq_text

    def test_covers_pip_install(self, faq_text: str):
        assert "pip install koai-verify" in faq_text

    def test_covers_module_direct_run(self, faq_text: str):
        assert "python -m koai_verify.cli" in faq_text


class TestFaqErrorSection:
    """오류 메시지 해석 FAQ 항목."""

    def test_covers_image_not_found_error(self, faq_text: str):
        assert "ImageNotFoundError" in faq_text

    def test_covers_url_not_allowed_error(self, faq_text: str):
        assert "UrlNotAllowedError" in faq_text

    def test_covers_unsupported_format_error(self, faq_text: str):
        assert "UnsupportedFormatError" in faq_text

    def test_covers_image_too_large_error(self, faq_text: str):
        assert "ImageTooLargeError" in faq_text

    def test_covers_image_corrupted_error(self, faq_text: str):
        assert "ImageCorruptedError" in faq_text


class TestFaqVerdictSection:
    """판정 결과 해석 FAQ 항목."""

    def test_covers_non_compliant(self, faq_text: str):
        assert "NON_COMPLIANT" in faq_text

    def test_covers_unknown(self, faq_text: str):
        assert "UNKNOWN" in faq_text

    def test_covers_rule_r03(self, faq_text: str):
        assert "R-03" in faq_text

    def test_covers_rule_r05(self, faq_text: str):
        assert "R-05" in faq_text

    def test_covers_rule_r07(self, faq_text: str):
        assert "R-07" in faq_text

    def test_covers_synthid(self, faq_text: str):
        assert "SynthID" in faq_text


class TestFaqJsSdkSection:
    """JS SDK FAQ 항목."""

    def test_covers_cli_not_found_code(self, faq_text: str):
        assert "CLI_NOT_FOUND" in faq_text

    def test_covers_image_not_found_code(self, faq_text: str):
        assert "IMAGE_NOT_FOUND" in faq_text

    def test_covers_json_parse_error_code(self, faq_text: str):
        assert "JSON_PARSE_ERROR" in faq_text

    def test_covers_verify_error_switch(self, faq_text: str):
        assert "switch" in faq_text

    def test_covers_koai_verify_cmd_env(self, faq_text: str):
        assert "KOAI_VERIFY_CMD" in faq_text


class TestFaqRobustnessSection:
    """강건성 테스트 FAQ 항목."""

    def test_covers_robustness_option(self, faq_text: str):
        assert "--robustness" in faq_text

    def test_covers_ci_recommendation(self, faq_text: str):
        assert "CI" in faq_text


class TestFaqLegalSection:
    """법령 관련 FAQ 항목."""

    def test_covers_article_31(self, faq_text: str):
        assert "제31조" in faq_text

    def test_covers_grace_period(self, faq_text: str):
        assert "2027" in faq_text

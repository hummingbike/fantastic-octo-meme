"""W18 — Next.js / FastAPI 통합 예제 및 퀵스타트 문서 업데이트 검증."""

from __future__ import annotations

from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent.parent
_EXAMPLES = _ROOT / "docs" / "examples"
_NEXTJS = _EXAMPLES / "nextjs_example.ts"
_FASTAPI = _EXAMPLES / "fastapi_example.py"
_QUICKSTART = _ROOT / "docs" / "quickstart.md"


# ── Task 2-A: Next.js 통합 예제 ───────────────────────────────────────────────


class TestNextjsExample:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return _NEXTJS.read_text(encoding="utf-8")

    def test_file_exists(self):
        assert _NEXTJS.exists(), "docs/examples/nextjs_example.ts 파일이 없습니다"

    def test_is_nonempty(self, content: str):
        assert len(content) > 300

    def test_imports_next_server(self, content: str):
        assert "next/server" in content

    def test_imports_koai_verify(self, content: str):
        assert "@koai/verify" in content

    def test_uses_verify(self, content: str):
        assert "verify(" in content

    def test_handles_verify_error(self, content: str):
        assert "VerifyError" in content

    def test_handles_error_code(self, content: str):
        assert "e.code" in content or ".code" in content

    def test_has_cli_not_found_branch(self, content: str):
        assert "CLI_NOT_FOUND" in content

    def test_has_file_upload_handling(self, content: str):
        assert "formData" in content or "FormData" in content

    def test_uses_tmp_file(self, content: str):
        assert "tmp" in content.lower() or "tmpdir" in content or "temp" in content.lower()

    def test_cleans_up_tmp_file(self, content: str):
        assert "unlink" in content or "finally" in content

    def test_returns_json_response(self, content: str):
        assert "NextResponse" in content

    def test_has_http_status_codes(self, content: str):
        assert "status:" in content or "{ status:" in content

    def test_has_post_handler(self, content: str):
        assert "POST" in content or "post" in content

    def test_no_hardcoded_real_paths(self, content: str):
        assert "/Users/okestro" not in content
        assert "/home/" not in content


# ── Task 2-B: FastAPI 통합 예제 ───────────────────────────────────────────────


class TestFastapiExample:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return _FASTAPI.read_text(encoding="utf-8")

    def test_file_exists(self):
        assert _FASTAPI.exists(), "docs/examples/fastapi_example.py 파일이 없습니다"

    def test_is_nonempty(self, content: str):
        assert len(content) > 300

    def test_imports_fastapi(self, content: str):
        assert "fastapi" in content.lower()

    def test_has_upload_file(self, content: str):
        assert "UploadFile" in content

    def test_imports_koai_verify(self, content: str):
        assert "koai_verify" in content or "from koai_verify" in content

    def test_uses_verify(self, content: str):
        assert "verify(" in content

    def test_handles_http_exception(self, content: str):
        assert "HTTPException" in content

    def test_handles_unsupported_format_error(self, content: str):
        assert "UnsupportedFormatError" in content

    def test_handles_image_too_large_error(self, content: str):
        assert "ImageTooLargeError" in content

    def test_handles_image_not_found_error(self, content: str):
        assert "ImageNotFoundError" in content

    def test_handles_image_corrupted_error(self, content: str):
        assert "ImageCorruptedError" in content

    def test_cleans_up_tmp_file(self, content: str):
        assert "finally" in content or "unlink" in content

    def test_uses_tmp_file(self, content: str):
        assert "tempfile" in content or "tmp" in content.lower()

    def test_has_app_instance(self, content: str):
        assert "FastAPI(" in content

    def test_has_post_endpoint(self, content: str):
        assert "@app.post" in content

    def test_returns_verdict(self, content: str):
        assert "verdict" in content

    def test_no_hardcoded_real_paths(self, content: str):
        assert "/Users/okestro" not in content
        assert "/home/" not in content


# ── Task 3: 퀵스타트 문서 FAQ 링크 + 오류 처리 섹션 ──────────────────────────


class TestQuickstartW18Updates:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return _QUICKSTART.read_text(encoding="utf-8")

    def test_quickstart_exists(self):
        assert _QUICKSTART.exists(), "docs/quickstart.md 파일이 없습니다"

    def test_faq_link_present(self, content: str):
        assert "faq.md" in content or "FAQ" in content

    def test_has_error_handling_section(self, content: str):
        assert "오류 처리" in content or "Error Handling" in content

    def test_shows_try_except_in_python(self, content: str):
        assert "try:" in content or "except" in content

    def test_shows_image_not_found_error(self, content: str):
        assert "ImageNotFoundError" in content or "ImageLoadError" in content

    def test_faq_file_exists(self):
        assert (_ROOT / "docs" / "faq.md").exists(), "docs/faq.md 파일이 없어 링크가 깨집니다"

    def test_has_next_steps_section(self, content: str):
        assert "다음 단계" in content or "Next Steps" in content

    def test_still_has_install_section(self, content: str):
        assert "pip install" in content

    def test_still_has_cli_section(self, content: str):
        assert "koai-verify" in content

    def test_still_has_python_api_section(self, content: str):
        assert "from koai_verify" in content

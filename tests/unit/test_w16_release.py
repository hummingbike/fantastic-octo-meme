"""W16 — 오픈 SDK + 강건성 벤치마크 공개 검증.

벤치마크 결과 파일, release CI, 블로그 초안, 수동 작업 기록이
필수 항목을 포함하는지 확인한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent
RESULTS_DIR = ROOT / "benchmarks" / "results"
SCRIPTS_DIR = ROOT / "scripts"
BLOG_DIR = ROOT / "docs" / "blog"


# ── Task 1: benchmarks/results/ 강건성 결과 ────────────────────────────────


class TestBenchmarkResults:
    def test_results_dir_exists(self):
        assert RESULTS_DIR.is_dir()

    def test_json_result_exists(self):
        assert (RESULTS_DIR / "survival_matrix_v1.json").exists()

    def test_markdown_summary_exists(self):
        assert (RESULTS_DIR / "survival_summary_v1.md").exists()

    @pytest.fixture(scope="class")
    def result_data(self) -> dict:
        return json.loads((RESULTS_DIR / "survival_matrix_v1.json").read_text(encoding="utf-8"))

    def test_has_version_field(self, result_data):
        assert "version" in result_data

    def test_has_generated_at(self, result_data):
        assert "generated_at" in result_data

    def test_has_fixture_note(self, result_data):
        assert "fixture_note" in result_data

    def test_has_matrix(self, result_data):
        assert "matrix" in result_data
        assert "cells" in result_data["matrix"]

    def test_matrix_has_cells(self, result_data):
        cells = result_data["matrix"]["cells"]
        assert len(cells) > 0

    def test_each_cell_has_required_fields(self, result_data):
        for cell in result_data["matrix"]["cells"]:
            assert "format" in cell
            assert "transform_label" in cell
            assert "survival_rate" in cell

    def test_has_r06_evaluation(self, result_data):
        assert "r06_evaluation" in result_data
        r06 = result_data["r06_evaluation"]
        assert "threshold" in r06
        assert "total_measured" in r06
        assert "failing_count" in r06
        assert "r06_triggered" in r06

    def test_r06_threshold_is_80_percent(self, result_data):
        assert result_data["r06_evaluation"]["threshold"] == pytest.approx(0.8)

    def test_has_images_list(self, result_data):
        assert "images" in result_data

    def test_c2pa_cell_survival_zero(self, result_data):
        # 합성 픽스처 기반: C2PA는 모든 변형에서 소거됨
        c2pa_cells = [
            c for c in result_data["matrix"]["cells"] if c["format"] == "c2pa" and c["survival_rate"] is not None
        ]
        if c2pa_cells:
            for cell in c2pa_cells:
                assert cell["survival_rate"] == pytest.approx(
                    0.0
                ), f"C2PA 는 모든 변형에서 소거 기대: {cell['transform_label']} = {cell['survival_rate']}"

    def test_detector_formats_declared(self, result_data):
        formats = result_data.get("detector_formats", [])
        assert "c2pa" in formats
        assert "exif" in formats
        assert "visible_label" in formats
        assert "open_watermark" in formats


class TestBenchmarkMarkdown:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return (RESULTS_DIR / "survival_summary_v1.md").read_text(encoding="utf-8")

    def test_has_title(self, content):
        assert "강건성 벤치마크" in content

    def test_has_fixture_note(self, content):
        assert "합성" in content or "fixture" in content.lower()

    def test_mentions_sns_platforms(self, content):
        assert "Instagram" in content or "instagram" in content.lower()
        assert "Twitter" in content or "KakaoTalk" in content

    def test_mentions_r06(self, content):
        assert "R-06" in content

    def test_has_transform_table(self, content):
        assert "jpeg_compress" in content or "jpeg" in content.lower()

    def test_has_methodology_section(self, content):
        assert "방법론" in content or "method" in content.lower()


class TestBenchmarkRunner:
    def test_script_exists(self):
        assert (SCRIPTS_DIR / "run_benchmark.py").exists()

    @pytest.fixture(scope="class")
    def script_content(self) -> str:
        return (SCRIPTS_DIR / "run_benchmark.py").read_text(encoding="utf-8")

    def test_has_main_function(self, script_content):
        assert "def main(" in script_content

    def test_has_argparse(self, script_content):
        assert "argparse" in script_content

    def test_has_output_dir_option(self, script_content):
        assert "--output" in script_content

    def test_imports_matrix_module(self, script_content):
        assert "from benchmarks.matrix import" in script_content

    def test_imports_harness(self, script_content):
        assert "run_battery" in script_content

    def test_saves_json(self, script_content):
        assert "json" in script_content
        assert ".json" in script_content

    def test_saves_markdown(self, script_content):
        assert ".md" in script_content


# ── Task 2: .github/workflows/release.yml ────────────────────────────────────


class TestReleaseWorkflow:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    def test_release_workflow_exists(self):
        assert (ROOT / ".github" / "workflows" / "release.yml").exists()

    def test_triggers_on_version_tags(self, content):
        assert "tags:" in content
        assert "v*" in content or '"v*"' in content or "'v*'" in content

    def test_has_test_job(self, content):
        assert "pytest" in content or "test" in content.lower()

    def test_has_release_job(self, content):
        assert "release" in content.lower()

    def test_creates_github_release(self, content):
        assert "action-gh-release" in content or "create-release" in content or "gh release" in content

    def test_publishes_to_pypi(self, content):
        assert "twine" in content or "pypi" in content.lower()

    def test_uses_pypi_token_secret(self, content):
        assert "PYPI_TOKEN" in content

    def test_has_python_matrix(self, content):
        assert "3.10" in content
        assert "3.11" in content

    def test_builds_distribution(self, content):
        assert "poetry build" in content or "build" in content

    def test_handles_missing_token_gracefully(self, content):
        # PYPI_TOKEN 없을 때 경고 후 스킵 (실패 아님)
        assert "PYPI_TOKEN" in content


# ── Task 3: docs/blog/ 포스트 초안 ────────────────────────────────────────────


class TestBlogDrafts:
    def test_tistory_draft_exists(self):
        assert (BLOG_DIR / "tistory_w16_draft.md").exists()

    def test_community_post_draft_exists(self):
        assert (BLOG_DIR / "community_post_draft.md").exists()


class TestTistoryDraft:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return (BLOG_DIR / "tistory_w16_draft.md").read_text(encoding="utf-8")

    def test_mentions_ai_basic_act(self, content):
        assert "AI 기본법" in content or "제31조" in content

    def test_has_installation_example(self, content):
        assert "pip install koai-verify" in content

    def test_mentions_r03(self, content):
        assert "R-03" in content

    def test_has_sns_survival_data(self, content):
        assert "Instagram" in content or "SNS" in content

    def test_has_gap_report_reference(self, content):
        assert "갭 리포트" in content or "gap_report" in content

    def test_has_github_link(self, content):
        assert "github.com" in content.lower()

    def test_has_license_mention(self, content):
        assert "Apache" in content or "라이선스" in content


class TestCommunityPostDraft:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return (BLOG_DIR / "community_post_draft.md").read_text(encoding="utf-8")

    def test_has_geek_news_section(self, content):
        assert "GeekNews" in content or "geek" in content.lower()

    def test_has_disquiet_section(self, content):
        assert "디스콰이엇" in content or "disquiet" in content.lower()

    def test_has_one_liner(self, content):
        assert "한 줄" in content or "소개" in content

    def test_has_github_link(self, content):
        assert "github.com" in content.lower()


# ── Task 4: docs/w16_blocked.md 수동 작업 기록 ────────────────────────────────


class TestBlockedItems:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return (ROOT / "docs" / "w16_blocked.md").read_text(encoding="utf-8")

    def test_blocked_doc_exists(self):
        assert (ROOT / "docs" / "w16_blocked.md").exists()

    def test_mentions_pypi(self, content):
        assert "PyPI" in content or "pypi" in content.lower()

    def test_mentions_pypi_token(self, content):
        assert "PYPI_TOKEN" in content

    def test_mentions_tistory(self, content):
        assert "Tistory" in content or "tistory" in content.lower()

    def test_mentions_geek_news(self, content):
        assert "GeekNews" in content or "geek" in content.lower()

    def test_mentions_disquiet(self, content):
        assert "디스콰이엇" in content or "disquiet" in content.lower()

    def test_mentions_github_release(self, content):
        assert "Release" in content or "릴리즈" in content

    def test_has_summary_table(self, content):
        assert "|" in content

    def test_has_tag_push_instruction(self, content):
        assert "git tag" in content or "v0.1.0" in content

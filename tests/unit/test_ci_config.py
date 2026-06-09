"""W5 Task2 — CI 설정 및 pyproject.toml 구조 검증.

인프라 파일이 필수 항목을 포함하는지 확인한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent


class TestPyprojectToml:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return (ROOT / "pyproject.toml").read_text()

    @pytest.fixture(scope="class")
    def parsed(self):
        if sys.version_info < (3, 11):
            pytest.skip("tomllib Python 3.11+ 전용")
        import tomllib

        return tomllib.loads((ROOT / "pyproject.toml").read_text())

    def test_file_exists(self):
        assert (ROOT / "pyproject.toml").exists()

    def test_has_poetry_section(self, content):
        assert "[tool.poetry]" in content

    def test_has_dependencies_section(self, content):
        assert "[tool.poetry.dependencies]" in content

    def test_has_dev_dependencies_section(self, content):
        assert "[tool.poetry.group.dev.dependencies]" in content

    def test_has_scripts_section(self, content):
        assert "[tool.poetry.scripts]" in content

    def test_cli_entry_point_defined(self, content):
        assert "koai-verify" in content
        assert "koai_verify.cli:main" in content

    def test_has_ruff_section(self, content):
        assert "[tool.ruff]" in content

    def test_has_black_section(self, content):
        assert "[tool.black]" in content

    def test_has_pytest_section(self, content):
        assert "[tool.pytest" in content

    def test_pillow_dependency_present(self, content):
        assert "Pillow" in content

    def test_piexif_dependency_present(self, content):
        assert "piexif" in content

    def test_c2pa_dependency_present(self, content):
        assert "c2pa-python" in content

    def test_parsed_name(self, parsed):
        assert parsed["tool"]["poetry"]["name"] == "koai-verify"

    def test_parsed_license(self, parsed):
        assert parsed["tool"]["poetry"]["license"] == "Apache-2.0"

    def test_parsed_scripts_key(self, parsed):
        scripts = parsed["tool"]["poetry"].get("scripts", {})
        assert "koai-verify" in scripts


class TestCiWorkflow:
    @pytest.fixture(scope="class")
    def ci_content(self) -> str:
        path = ROOT / ".github" / "workflows" / "ci.yml"
        return path.read_text()

    def test_ci_file_exists(self):
        assert (ROOT / ".github" / "workflows" / "ci.yml").exists()

    def test_ci_triggers_on_push(self, ci_content):
        assert "push" in ci_content

    def test_ci_triggers_on_pull_request(self, ci_content):
        assert "pull_request" in ci_content

    def test_ci_runs_pytest(self, ci_content):
        assert "pytest" in ci_content

    def test_ci_runs_ruff(self, ci_content):
        assert "ruff" in ci_content

    def test_ci_runs_black(self, ci_content):
        assert "black" in ci_content

    def test_ci_targets_main_branch(self, ci_content):
        assert '"main"' in ci_content or "'main'" in ci_content or "main" in ci_content

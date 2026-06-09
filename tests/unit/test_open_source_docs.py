"""W13 — 오픈소스 공개 준비 파일 검증.

README, CONTRIBUTING, LICENSE, quickstart, ISSUE_TEMPLATE 이 필수 항목을 포함하는지 확인한다.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


class TestReadme:
    def setup_method(self):
        self.content = (ROOT / "README.md").read_text(encoding="utf-8")

    def test_readme_exists(self):
        assert (ROOT / "README.md").exists()

    def test_has_korean_title_or_description(self):
        assert "한국" in self.content or "KoAI" in self.content

    def test_has_english_description(self):
        assert "Open-source" in self.content or "SDK" in self.content

    def test_has_quick_start_section(self):
        lower = self.content.lower()
        assert "quick start" in lower or "빠른 시작" in self.content

    def test_has_pip_install(self):
        assert "pip install koai-verify" in self.content

    def test_has_cli_usage(self):
        assert "koai-verify" in self.content

    def test_has_python_api_example(self):
        assert "from koai_verify import" in self.content or "import koai_verify" in self.content

    def test_has_license_reference(self):
        assert "Apache" in self.content or "LICENSE" in self.content

    def test_has_contributing_reference(self):
        assert "CONTRIBUTING" in self.content

    def test_has_rule_section(self):
        assert "R-01" in self.content or "룰" in self.content or "Rule" in self.content

    def test_has_verdict_values(self):
        assert "COMPLIANT" in self.content
        assert "NON_COMPLIANT" in self.content

    def test_has_js_sdk_reference(self):
        assert "@koai/verify" in self.content or "npm install" in self.content


class TestContributing:
    def setup_method(self):
        self.content = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    def test_contributing_exists(self):
        assert (ROOT / "CONTRIBUTING.md").exists()

    def test_has_code_style_section(self):
        assert "코드 스타일" in self.content or "Code Style" in self.content

    def test_mentions_black(self):
        assert "black" in self.content

    def test_mentions_ruff(self):
        assert "ruff" in self.content

    def test_mentions_type_hints(self):
        assert "type hint" in self.content.lower() or "type_hints" in self.content or "타입" in self.content

    def test_has_commit_convention(self):
        assert "feat:" in self.content or "커밋 규칙" in self.content

    def test_has_test_requirements(self):
        assert "pytest" in self.content or "테스트" in self.content

    def test_no_mock_policy(self):
        assert "mock" in self.content.lower()

    def test_has_pr_process(self):
        assert "PR" in self.content or "Pull Request" in self.content

    def test_has_security_notes(self):
        assert "SSRF" in self.content or "보안" in self.content or "Security" in self.content

    def test_has_unknown_policy(self):
        assert "UNKNOWN" in self.content


class TestLicense:
    def setup_method(self):
        self.content = (ROOT / "LICENSE").read_text(encoding="utf-8")

    def test_license_exists(self):
        assert (ROOT / "LICENSE").exists()

    def test_is_apache_2(self):
        assert "Apache License" in self.content
        assert "Version 2.0" in self.content

    def test_has_terms_and_conditions(self):
        assert "TERMS AND CONDITIONS" in self.content

    def test_not_empty(self):
        assert len(self.content.strip()) > 100


class TestQuickstart:
    def setup_method(self):
        self.path = ROOT / "docs" / "quickstart.md"
        self.content = self.path.read_text(encoding="utf-8")

    def test_quickstart_exists(self):
        assert self.path.exists()

    def test_has_installation_section(self):
        assert "pip install" in self.content

    def test_has_cli_example(self):
        assert "koai-verify" in self.content

    def test_has_python_api_example(self):
        assert "from koai_verify" in self.content or "verify(" in self.content

    def test_has_verdict_explanation(self):
        assert "COMPLIANT" in self.content
        assert "NON_COMPLIANT" in self.content

    def test_has_r03_explanation(self):
        assert "R-03" in self.content

    def test_has_js_sdk_section(self):
        assert "@koai/verify" in self.content or "npm install" in self.content

    def test_has_next_steps(self):
        assert "다음 단계" in self.content or "Next Step" in self.content


class TestIssueTemplates:
    def test_issue_template_dir_exists(self):
        assert (ROOT / ".github" / "ISSUE_TEMPLATE").is_dir()

    def test_bug_report_template_exists(self):
        assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md").exists()

    def test_feature_request_template_exists(self):
        assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.md").exists()

    def test_bug_report_has_frontmatter(self):
        content = (ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md").read_text(encoding="utf-8")
        assert "name:" in content
        assert "labels:" in content
        assert "bug" in content

    def test_feature_request_has_frontmatter(self):
        content = (ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.md").read_text(encoding="utf-8")
        assert "name:" in content
        assert "labels:" in content
        assert "enhancement" in content

    def test_bug_report_has_reproduce_section(self):
        content = (ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md").read_text(encoding="utf-8")
        assert "Steps to Reproduce" in content or "재현" in content

    def test_feature_request_has_problem_section(self):
        content = (ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.md").read_text(encoding="utf-8")
        assert "Problem" in content or "문제" in content

    def test_bug_report_mentions_environment(self):
        content = (ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md").read_text(encoding="utf-8")
        assert "Environment" in content or "환경" in content

    def test_feature_request_mentions_regulation(self):
        content = (ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.md").read_text(encoding="utf-8")
        assert "R-" in content or "법령" in content or "Regulation" in content

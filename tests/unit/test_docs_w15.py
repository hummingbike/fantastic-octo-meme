"""W15 — 문서·예제 정비 검증.

docs/examples/, .github/workflows/koai-verify.yml, README.md 업데이트,
docs/architecture.md 가 필수 항목을 포함하는지 확인한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent
EXAMPLES_DIR = ROOT / "docs" / "examples"
ARCH_DOC = ROOT / "docs" / "architecture.md"
WORKFLOW = ROOT / ".github" / "workflows" / "koai-verify.yml"


# ── Task 1: docs/examples/ 언어별 사용 예제 ──────────────────────────────────


class TestExamplesDir:
    def test_examples_dir_exists(self):
        assert EXAMPLES_DIR.is_dir()

    def test_python_example_exists(self):
        assert (EXAMPLES_DIR / "python_example.py").exists()

    def test_node_example_exists(self):
        ts = (EXAMPLES_DIR / "node_example.ts").exists()
        js = (EXAMPLES_DIR / "node_example.js").exists()
        assert ts or js, "node_example.ts 또는 node_example.js 가 없음"

    def test_curl_example_exists(self):
        sh = (EXAMPLES_DIR / "curl_example.sh").exists()
        md = (EXAMPLES_DIR / "curl_example.md").exists()
        assert sh or md, "curl_example.sh 또는 curl_example.md 가 없음"


class TestPythonExample:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return (EXAMPLES_DIR / "python_example.py").read_text(encoding="utf-8")

    def test_imports_koai_verify(self, content):
        assert "from koai_verify" in content or "import koai_verify" in content

    def test_uses_verify_function(self, content):
        assert "verify(" in content

    def test_handles_verdict(self, content):
        assert "verdict" in content

    def test_shows_non_compliant_case(self, content):
        assert "NON_COMPLIANT" in content

    def test_has_robustness_example(self, content):
        assert "robustness" in content

    def test_has_batch_example(self, content):
        assert "batch" in content.lower() or "glob" in content or "배치" in content

    def test_no_hardcoded_real_paths(self, content):
        # 예제에 하드코딩된 실제 파일 경로가 없어야 함
        assert "/home/" not in content
        assert "/Users/okestro" not in content


class TestNodeExample:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        path = EXAMPLES_DIR / "node_example.ts"
        if not path.exists():
            path = EXAMPLES_DIR / "node_example.js"
        return path.read_text(encoding="utf-8")

    def test_imports_koai_verify(self, content):
        assert "@koai/verify" in content

    def test_uses_verify_function(self, content):
        assert "verify(" in content

    def test_handles_verdict(self, content):
        assert "verdict" in content

    def test_has_ci_example(self, content):
        assert "exit" in content or "CI" in content or "process.exit" in content

    def test_handles_non_compliant(self, content):
        assert "NON_COMPLIANT" in content


class TestCurlExample:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        path = EXAMPLES_DIR / "curl_example.sh"
        if not path.exists():
            path = EXAMPLES_DIR / "curl_example.md"
        return path.read_text(encoding="utf-8")

    def test_uses_koai_verify_cli(self, content):
        assert "koai-verify" in content

    def test_shows_format_options(self, content):
        assert "--format" in content or "summary" in content

    def test_shows_robustness_option(self, content):
        assert "--robustness" in content

    def test_shows_exit_codes(self, content):
        # 종료 코드 설명이 있어야 함
        assert "exit" in content.lower() or "종료" in content

    def test_has_batch_pattern(self, content):
        assert "for" in content or "배치" in content or "batch" in content.lower()


# ── Task 2: .github/workflows/koai-verify.yml ────────────────────────────────


class TestKoaiVerifyWorkflow:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_file_exists(self):
        assert WORKFLOW.exists()

    def test_has_name(self, content):
        assert "name:" in content

    def test_has_on_trigger(self, content):
        assert "\non:" in content or "on:" in content

    def test_triggers_on_pull_request(self, content):
        assert "pull_request" in content

    def test_has_jobs_section(self, content):
        assert "jobs:" in content

    def test_installs_koai_verify(self, content):
        assert "koai-verify" in content
        assert "pip install" in content

    def test_uses_python_setup(self, content):
        assert "setup-python" in content or "python" in content

    def test_handles_non_compliant_exit(self, content):
        assert "exit 1" in content or "NON_COMPLIANT" in content

    def test_references_images(self, content):
        # 이미지 파일 경로/패턴 참조
        assert ".jpg" in content or ".png" in content or "images" in content

    def test_valid_yaml_structure(self, content):
        # 기본 YAML 구조 확인 (PyYAML 없이)
        assert "name:" in content
        assert "on:" in content or "\non:" in content
        assert "jobs:" in content
        assert "steps:" in content


# ── Task 3: README.md 배지 업데이트 및 갭 리포트 링크 ──────────────────────────


class TestReadmeW15Updates:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return (ROOT / "README.md").read_text(encoding="utf-8")

    def test_has_pypi_badge(self, content):
        assert "pypi" in content.lower() or "PyPI" in content

    def test_has_gap_report_link(self, content):
        assert "gap_report_v1" in content or "갭 리포트" in content

    def test_has_examples_reference(self, content):
        assert "examples" in content.lower() or "예제" in content

    def test_has_architecture_reference(self, content):
        assert "architecture" in content.lower() or "아키텍처" in content

    def test_existing_ci_badge_intact(self, content):
        assert "ci.yml/badge.svg" in content

    def test_existing_license_badge_intact(self, content):
        assert "Apache" in content


# ── Task 4: docs/architecture.md ──────────────────────────────────────────────


class TestArchitectureDoc:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return ARCH_DOC.read_text(encoding="utf-8")

    def test_architecture_doc_exists(self):
        assert ARCH_DOC.exists()

    def test_has_system_overview_section(self, content):
        assert "overview" in content.lower() or "전체 구조" in content or "Overview" in content

    def test_describes_detectors(self, content):
        assert "Detector" in content or "탐지" in content

    def test_lists_all_four_detectors(self, content):
        assert "C2PA" in content
        assert "EXIF" in content
        assert "OCR" in content
        assert "Watermark" in content or "워터마크" in content

    def test_describes_rule_engine(self, content):
        assert "RuleEngine" in content or "룰 엔진" in content

    def test_references_all_rules(self, content):
        for rule in ["R-01", "R-02", "R-03", "R-04", "R-05", "R-06", "R-07"]:
            assert rule in content, f"{rule} 이 아키텍처 문서에 없음"

    def test_r03_highlighted(self, content):
        # R-03은 핵심 규칙 — 강조 표시 필요
        assert "R-03" in content
        # 핵심 또는 NON_COMPLIANT 언급 확인
        assert "NON_COMPLIANT" in content or "핵심" in content

    def test_describes_robustness_harness(self, content):
        assert "robustness" in content.lower() or "강건성" in content

    def test_describes_report_format(self, content):
        assert "report" in content.lower() or "리포트" in content

    def test_has_directory_structure(self, content):
        assert "koai_verify/" in content

    def test_has_verdict_table(self, content):
        assert "COMPLIANT" in content
        assert "WARNING" in content
        assert "UNKNOWN" in content

    def test_has_pipeline_description(self, content):
        assert "pipeline" in content.lower() or "파이프라인" in content

    def test_has_related_docs_section(self, content):
        assert "관련 문서" in content or "Related" in content

    def test_references_prd(self, content):
        assert "PRD" in content

    def test_references_gap_report(self, content):
        assert "gap_report" in content or "갭 리포트" in content

"""W24 — 규제 변경 모니터링 자동화: regulation_monitor.py, CLI 스크립트, 워크플로, 문서 검증."""

from __future__ import annotations

from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent.parent
_MONITOR_MOD = _ROOT / "koai_verify" / "standards" / "regulation_monitor.py"
_SCRIPT = _ROOT / "scripts" / "check_regulation_updates.py"
_WORKFLOW = _ROOT / ".github" / "workflows" / "regulation_monitor.yml"
_DOC = _ROOT / "docs" / "regulation_monitoring.md"


# ─────────────────────────────────────────────────────────────────────────────
# Task 1: koai_verify/standards/regulation_monitor.py
# ─────────────────────────────────────────────────────────────────────────────


class TestRegulationMonitorModuleStructure:
    def test_module_exists(self):
        assert _MONITOR_MOD.exists()

    def test_module_nonempty(self):
        assert len(_MONITOR_MOD.read_text(encoding="utf-8")) > 500

    def test_module_imports_cleanly(self):
        from koai_verify.standards.regulation_monitor import MONITORED_SOURCES, RegulationMonitor

        assert MONITORED_SOURCES is not None
        assert RegulationMonitor is not None

    def test_exported_from_standards_package(self):
        from koai_verify.standards import MONITORED_SOURCES, RegulationMonitor

        assert MONITORED_SOURCES is not None
        assert RegulationMonitor is not None


class TestMonitoredSources:
    def test_has_at_least_four_sources(self):
        from koai_verify.standards.regulation_monitor import MONITORED_SOURCES

        assert len(MONITORED_SOURCES) >= 4

    def test_sources_have_required_fields(self):
        from koai_verify.standards.regulation_monitor import MONITORED_SOURCES

        for source in MONITORED_SOURCES:
            assert source.name
            assert source.url.startswith("https://")
            assert source.description

    def test_includes_tta_portal(self):
        from koai_verify.standards.regulation_monitor import MONITORED_SOURCES

        assert any("tta.or.kr" in s.url for s in MONITORED_SOURCES)

    def test_includes_msit(self):
        from koai_verify.standards.regulation_monitor import MONITORED_SOURCES

        assert any("msit.go.kr" in s.url for s in MONITORED_SOURCES)

    def test_source_names_are_unique(self):
        from koai_verify.standards.regulation_monitor import MONITORED_SOURCES

        names = [s.name for s in MONITORED_SOURCES]
        assert len(names) == len(set(names))


class TestComputeContentHash:
    def test_same_content_same_hash(self):
        from koai_verify.standards.regulation_monitor import compute_content_hash

        assert compute_content_hash("hello") == compute_content_hash("hello")

    def test_different_content_different_hash(self):
        from koai_verify.standards.regulation_monitor import compute_content_hash

        assert compute_content_hash("hello") != compute_content_hash("world")

    def test_returns_hex_string(self):
        from koai_verify.standards.regulation_monitor import compute_content_hash

        h = compute_content_hash("hello")
        assert len(h) == 64
        int(h, 16)  # raises ValueError if not valid hex


class TestRegulationMonitorCheck:
    def _make_source(self, name: str = "test_source"):
        from koai_verify.standards.regulation_monitor import MonitorSource

        return MonitorSource(name=name, url="https://example.invalid/notice", description="테스트 소스")

    def test_first_check_is_not_changed(self):
        from koai_verify.standards.regulation_monitor import RegulationMonitor

        monitor = RegulationMonitor(fetcher=lambda url: "content-v1")
        result = monitor.check(self._make_source())
        assert result.changed is False
        assert result.previous_hash is None

    def test_second_check_same_content_not_changed(self):
        from koai_verify.standards.regulation_monitor import RegulationMonitor

        monitor = RegulationMonitor(fetcher=lambda url: "content-v1")
        source = self._make_source()
        monitor.check(source)
        result = monitor.check(source)
        assert result.changed is False

    def test_second_check_different_content_is_changed(self):
        from koai_verify.standards.regulation_monitor import RegulationMonitor

        contents = iter(["content-v1", "content-v2"])
        monitor = RegulationMonitor(fetcher=lambda url: next(contents))
        source = self._make_source()
        monitor.check(source)
        result = monitor.check(source)
        assert result.changed is True
        assert result.previous_hash is not None
        assert result.previous_hash != result.current_hash

    def test_check_all_checks_every_source(self):
        from koai_verify.standards.regulation_monitor import RegulationMonitor

        sources = [self._make_source("a"), self._make_source("b"), self._make_source("c")]
        monitor = RegulationMonitor(fetcher=lambda url: "fixed")
        results = monitor.check_all(sources)
        assert len(results) == 3
        assert {r.source_name for r in results} == {"a", "b", "c"}

    def test_check_all_defaults_to_monitored_sources(self):
        from koai_verify.standards.regulation_monitor import MONITORED_SOURCES, RegulationMonitor

        monitor = RegulationMonitor(fetcher=lambda url: "fixed")
        results = monitor.check_all()
        assert len(results) == len(MONITORED_SOURCES)

    def test_result_has_checked_at_timestamp(self):
        from koai_verify.standards.regulation_monitor import RegulationMonitor

        monitor = RegulationMonitor(fetcher=lambda url: "content")
        result = monitor.check(self._make_source())
        assert result.checked_at.endswith("Z")

    def test_fetcher_receives_source_url(self):
        from koai_verify.standards.regulation_monitor import RegulationMonitor

        received_urls = []
        monitor = RegulationMonitor(fetcher=lambda url: received_urls.append(url) or "content")
        source = self._make_source()
        monitor.check(source)
        assert received_urls == [source.url]


class TestRegulationMonitorStatePersistence:
    def _make_source(self):
        from koai_verify.standards.regulation_monitor import MonitorSource

        return MonitorSource(name="persisted_source", url="https://example.invalid", description="d")

    def test_state_file_created(self, tmp_path):
        from koai_verify.standards.regulation_monitor import RegulationMonitor

        state_path = tmp_path / "state.json"
        monitor = RegulationMonitor(fetcher=lambda url: "content", state_path=state_path)
        monitor.check(self._make_source())
        assert state_path.exists()

    def test_state_persisted_across_instances(self, tmp_path):
        from koai_verify.standards.regulation_monitor import RegulationMonitor

        state_path = tmp_path / "state.json"
        source = self._make_source()

        monitor1 = RegulationMonitor(fetcher=lambda url: "content-v1", state_path=state_path)
        monitor1.check(source)

        contents = iter(["content-v2"])
        monitor2 = RegulationMonitor(fetcher=lambda url: next(contents), state_path=state_path)
        result = monitor2.check(source)

        assert result.changed is True

    def test_missing_state_file_starts_fresh(self, tmp_path):
        from koai_verify.standards.regulation_monitor import RegulationMonitor

        state_path = tmp_path / "does_not_exist.json"
        monitor = RegulationMonitor(fetcher=lambda url: "content", state_path=state_path)
        result = monitor.check(self._make_source())
        assert result.changed is False

    def test_corrupt_state_file_starts_fresh(self, tmp_path):
        from koai_verify.standards.regulation_monitor import RegulationMonitor

        state_path = tmp_path / "state.json"
        state_path.write_text("not-json", encoding="utf-8")
        monitor = RegulationMonitor(fetcher=lambda url: "content", state_path=state_path)
        result = monitor.check(self._make_source())
        assert result.changed is False

    def test_no_state_path_skips_persistence(self):
        from koai_verify.standards.regulation_monitor import RegulationMonitor

        monitor = RegulationMonitor(fetcher=lambda url: "content", state_path=None)
        result = monitor.check(self._make_source())
        assert result.changed is False


# ─────────────────────────────────────────────────────────────────────────────
# Task 2: scripts/check_regulation_updates.py
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckScript:
    def test_script_exists(self):
        assert _SCRIPT.exists()

    def test_script_nonempty(self):
        assert len(_SCRIPT.read_text(encoding="utf-8")) > 300

    def test_script_uses_default_fetcher(self):
        content = _SCRIPT.read_text(encoding="utf-8")
        assert "default_fetcher" in content

    def test_main_returns_zero_when_no_changes(self, monkeypatch):
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_regulation_updates", _SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        from koai_verify.standards.regulation_monitor import RegulationMonitor

        monkeypatch.setattr(
            module,
            "RegulationMonitor",
            lambda fetcher, state_path=None: RegulationMonitor(fetcher=lambda url: "fixed", state_path=None),
        )
        assert module.main() == 0


# ─────────────────────────────────────────────────────────────────────────────
# Task 3: .github/workflows/regulation_monitor.yml
# ─────────────────────────────────────────────────────────────────────────────


class TestRegulationMonitorWorkflow:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return _WORKFLOW.read_text(encoding="utf-8")

    def test_file_exists(self):
        assert _WORKFLOW.exists()

    def test_has_schedule_trigger(self, content: str):
        assert "schedule" in content
        assert "cron" in content

    def test_has_manual_dispatch_trigger(self, content: str):
        assert "workflow_dispatch" in content

    def test_runs_check_script(self, content: str):
        assert "check_regulation_updates.py" in content

    def test_has_issues_write_permission(self, content: str):
        assert "issues: write" in content

    def test_has_contents_write_permission(self, content: str):
        assert "contents: write" in content

    def test_uses_gh_issue_create_on_change(self, content: str):
        assert "gh issue create" in content

    def test_commits_state_file(self, content: str):
        assert ".regulation_monitor_state.json" in content


# ─────────────────────────────────────────────────────────────────────────────
# Task 4: docs/regulation_monitoring.md
# ─────────────────────────────────────────────────────────────────────────────


class TestRegulationMonitoringDocument:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return _DOC.read_text(encoding="utf-8")

    def test_file_exists(self):
        assert _DOC.exists()

    def test_is_nonempty(self, content: str):
        assert len(content) > 1000

    def test_starts_with_heading(self, content: str):
        assert content.startswith("#")

    def test_has_background_section(self, content: str):
        assert "배경" in content

    def test_references_tta_submission_process(self, content: str):
        assert "tta_contact.py" in content or "SUBMISSION_PROCESS" in content

    def test_documents_monitored_sources_table(self, content: str):
        for name in ("msit_press_release", "nia_guideline_notice", "tta_tc010_portal", "law_go_kr_ai_act"):
            assert name in content

    def test_documents_github_actions_automation(self, content: str):
        assert "GitHub Actions" in content

    def test_mentions_cron_schedule(self, content: str):
        assert "월요일" in content or "cron" in content

    def test_has_limitations_section(self, content: str):
        assert "한계" in content

    def test_mentions_hash_comparison_limitation(self, content: str):
        assert "해시" in content

    def test_mentions_manual_rule_review_still_required(self, content: str):
        assert "수동" in content

    def test_no_hardcoded_personal_paths(self, content: str):
        assert "/Users/okestro" not in content

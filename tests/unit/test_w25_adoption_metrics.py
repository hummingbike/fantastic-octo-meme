"""W25 — 2분기 회고: adoption_metrics.py, 수집 스크립트, 회고 문서, 모니터 오류 처리 검증."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from koai_verify.analysis.adoption_metrics import (
    GITHUB_API_URL,
    NPM_API_URL,
    PRD_TARGETS,
    PYPI_API_URL,
    AdoptionSnapshot,
    MetricStatus,
    collect_snapshot,
    evaluate_metric,
    evaluate_q2_gate,
    evaluate_snapshot,
    fetch_github_stats,
    fetch_npm_status,
    fetch_pypi_status,
    format_snapshot_markdown,
)

_ROOT = Path(__file__).parent.parent.parent
_SCRIPT = _ROOT / "scripts" / "collect_adoption_metrics.py"
_DOC = _ROOT / "docs" / "retrospective_q2.md"
_MONITOR_WORKFLOW = _ROOT / ".github" / "workflows" / "regulation_monitor.yml"


def _http_error(code: int) -> HTTPError:
    return HTTPError("https://example.test", code, "err", hdrs=None, fp=None)


# ─────────────────────────────────────────────────────────────────────────────
# PRD §5 목표 테이블
# ─────────────────────────────────────────────────────────────────────────────


class TestPrdTargets:
    def test_has_three_milestones(self):
        assert set(PRD_TARGETS) == {"W16", "W40", "W52"}

    def test_w16_github_star_target_is_50(self):
        assert PRD_TARGETS["W16"]["github_stars"] == 50

    def test_targets_monotonically_increase(self):
        assert PRD_TARGETS["W16"]["github_stars"] < PRD_TARGETS["W40"]["github_stars"]
        assert PRD_TARGETS["W40"]["github_stars"] < PRD_TARGETS["W52"]["github_stars"]

    def test_w16_has_no_integration_target(self):
        assert PRD_TARGETS["W16"]["external_integrations"] is None


# ─────────────────────────────────────────────────────────────────────────────
# AdoptionSnapshot 직렬화
# ─────────────────────────────────────────────────────────────────────────────


class TestAdoptionSnapshot:
    def test_defaults_are_unknown(self):
        snap = AdoptionSnapshot()
        assert snap.github_stars is None
        assert snap.pypi_published is None
        assert snap.weekly_installs is None

    def test_roundtrip(self):
        snap = AdoptionSnapshot(github_stars=3, pypi_published=True, pypi_latest_version="0.2.0")
        restored = AdoptionSnapshot.from_dict(snap.to_dict())
        assert restored == snap

    def test_from_dict_ignores_unknown_keys(self):
        snap = AdoptionSnapshot.from_dict({"github_stars": 1, "not_a_field": "x"})
        assert snap.github_stars == 1

    def test_collected_at_is_iso_utc(self):
        assert AdoptionSnapshot().collected_at.endswith("Z")


# ─────────────────────────────────────────────────────────────────────────────
# fetch 계층 (가짜 fetcher — 실제 네트워크 접근 없음)
# ─────────────────────────────────────────────────────────────────────────────


class TestFetchGithubStats:
    def test_positive(self):
        payload = json.dumps({"stargazers_count": 7, "forks_count": 2, "subscribers_count": 3, "open_issues_count": 1})
        stats = fetch_github_stats(lambda url: payload)
        assert stats == {"stars": 7, "forks": 2, "watchers": 3, "open_issues": 1}

    def test_network_failure_returns_all_none(self):
        def failing(url: str) -> str:
            raise URLError("timed out")

        stats = fetch_github_stats(failing)
        assert all(v is None for v in stats.values())

    def test_malformed_json_returns_all_none(self):
        stats = fetch_github_stats(lambda url: "<html>not json</html>")
        assert all(v is None for v in stats.values())


class TestFetchPypiStatus:
    def test_published(self):
        payload = json.dumps({"info": {"version": "0.1.0"}})
        assert fetch_pypi_status(lambda url: payload) == (True, "0.1.0")

    def test_404_means_unpublished(self):
        def not_found(url: str) -> str:
            raise _http_error(404)

        assert fetch_pypi_status(not_found) == (False, None)

    def test_server_error_is_unknown(self):
        def broken(url: str) -> str:
            raise _http_error(503)

        assert fetch_pypi_status(broken) == (None, None)

    def test_network_failure_is_unknown(self):
        def failing(url: str) -> str:
            raise URLError("no route")

        assert fetch_pypi_status(failing) == (None, None)


class TestFetchNpmStatus:
    def test_published(self):
        assert fetch_npm_status(lambda url: "{}") is True

    def test_404_means_unpublished(self):
        def not_found(url: str) -> str:
            raise _http_error(404)

        assert fetch_npm_status(not_found) is False

    def test_network_failure_is_unknown(self):
        def failing(url: str) -> str:
            raise URLError("timed out")

        assert fetch_npm_status(failing) is None


class TestCollectSnapshot:
    def test_routes_by_url(self):
        def fake(url: str) -> str:
            if url == GITHUB_API_URL:
                return json.dumps(
                    {
                        "stargazers_count": 5,
                        "forks_count": 1,
                        "subscribers_count": 2,
                        "open_issues_count": 0,
                    }
                )
            if url == PYPI_API_URL:
                return json.dumps({"info": {"version": "0.2.0"}})
            if url == NPM_API_URL:
                raise _http_error(404)
            raise AssertionError(f"unexpected url: {url}")

        snap = collect_snapshot(fake)
        assert snap.github_stars == 5
        assert snap.pypi_published is True
        assert snap.pypi_latest_version == "0.2.0"
        assert snap.npm_published is False

    def test_unmeasurable_fields_stay_unknown(self):
        snap = collect_snapshot(lambda url: (_ for _ in ()).throw(URLError("down")))
        assert snap.weekly_installs is None
        assert snap.api_signups is None


# ─────────────────────────────────────────────────────────────────────────────
# 평가 로직
# ─────────────────────────────────────────────────────────────────────────────


class TestEvaluateMetric:
    def test_met(self):
        assert evaluate_metric("github_stars", 60, 50).status is MetricStatus.MET

    def test_exactly_at_target_is_met(self):
        assert evaluate_metric("github_stars", 50, 50).status is MetricStatus.MET

    def test_not_met(self):
        assert evaluate_metric("github_stars", 0, 50).status is MetricStatus.NOT_MET

    def test_unmeasured_is_unknown(self):
        assert evaluate_metric("weekly_installs", None, 1).status is MetricStatus.UNKNOWN

    def test_no_target_is_not_applicable(self):
        assert evaluate_metric("api_signups", 3, None).status is MetricStatus.NOT_APPLICABLE


class TestEvaluateSnapshot:
    def test_w16_evaluation(self):
        snap = AdoptionSnapshot(github_stars=0, external_integrations=0)
        by_name = {a.metric: a for a in evaluate_snapshot(snap, milestone="W16")}
        assert by_name["github_stars"].status is MetricStatus.NOT_MET
        assert by_name["weekly_installs"].status is MetricStatus.UNKNOWN
        assert by_name["external_integrations"].status is MetricStatus.NOT_APPLICABLE

    def test_w40_integration_target_applies(self):
        snap = AdoptionSnapshot(external_integrations=2)
        by_name = {a.metric: a for a in evaluate_snapshot(snap, milestone="W40")}
        assert by_name["external_integrations"].status is MetricStatus.MET

    def test_unknown_milestone_raises(self):
        with pytest.raises(ValueError):
            evaluate_snapshot(AdoptionSnapshot(), milestone="W99")


class TestEvaluateQ2Gate:
    def test_gate_has_three_items(self):
        assert len(evaluate_q2_gate(AdoptionSnapshot())) == 3

    def test_sdk_open_passes_when_pypi_published(self):
        gate = {g.name: g for g in evaluate_q2_gate(AdoptionSnapshot(pypi_published=True))}
        assert gate["오픈 SDK 공개"].passed is True

    def test_sdk_open_unknown_when_unmeasured(self):
        gate = {g.name: g for g in evaluate_q2_gate(AdoptionSnapshot(pypi_published=None))}
        assert gate["오픈 SDK 공개"].passed is None

    def test_integrations_fail_below_two(self):
        gate = {g.name: g for g in evaluate_q2_gate(AdoptionSnapshot(external_integrations=0))}
        assert gate["외부 통합 ≥2"].passed is False

    def test_integrations_pass_at_two(self):
        gate = {g.name: g for g in evaluate_q2_gate(AdoptionSnapshot(external_integrations=2))}
        assert gate["외부 통합 ≥2"].passed is True

    def test_integrations_unknown_when_unmeasured(self):
        gate = {g.name: g for g in evaluate_q2_gate(AdoptionSnapshot())}
        assert gate["외부 통합 ≥2"].passed is None


class TestFormatSnapshotMarkdown:
    def test_renders_tables(self):
        snap = AdoptionSnapshot(github_stars=0, pypi_published=True)
        md = format_snapshot_markdown(snap, evaluate_snapshot(snap), evaluate_q2_gate(snap), milestone="W16")
        assert "| 지표 | 실측 | W16 목표 | 판정 |" in md
        assert "NOT_MET" in md
        assert "Q2 게이트" in md

    def test_unknown_rendered_explicitly(self):
        snap = AdoptionSnapshot()
        md = format_snapshot_markdown(snap, evaluate_snapshot(snap), evaluate_q2_gate(snap))
        assert "UNKNOWN" in md


# ─────────────────────────────────────────────────────────────────────────────
# 산출물: 수집 스크립트 + 회고 문서
# ─────────────────────────────────────────────────────────────────────────────


class TestArtifacts:
    def test_collect_script_exists(self):
        assert _SCRIPT.exists()

    def test_collect_script_uses_injected_fetcher_module(self):
        text = _SCRIPT.read_text(encoding="utf-8")
        assert "collect_snapshot" in text
        assert "default_fetcher" in text

    def test_retrospective_doc_exists(self):
        assert _DOC.exists()

    def test_retrospective_doc_covers_gate_and_metrics(self):
        text = _DOC.read_text(encoding="utf-8")
        assert "Q2 게이트" in text
        assert "GitHub ★" in text
        assert "3분기" in text


# ─────────────────────────────────────────────────────────────────────────────
# W25 수정: 규제 모니터 fetch 실패를 변경으로 오인하지 않음
# ─────────────────────────────────────────────────────────────────────────────


class TestRegulationMonitorFetchErrorHandling:
    def _source(self):
        from koai_verify.standards.regulation_monitor import MonitorSource

        return MonitorSource(name="test_src", url="https://example.test", description="테스트")

    def test_fetch_error_is_not_a_change(self, tmp_path):
        from koai_verify.standards.regulation_monitor import RegulationMonitor

        def failing(url: str) -> str:
            raise TimeoutError("timed out")

        monitor = RegulationMonitor(fetcher=failing, state_path=tmp_path / "state.json")
        result = monitor.check(self._source())
        assert result.changed is False
        assert result.error is not None
        assert "TimeoutError" in result.error

    def test_fetch_error_does_not_overwrite_state(self, tmp_path):
        from koai_verify.standards.regulation_monitor import RegulationMonitor

        state_path = tmp_path / "state.json"
        source = self._source()
        baseline = RegulationMonitor(fetcher=lambda url: "v1", state_path=state_path)
        baseline.check(source)

        def failing(url: str) -> str:
            raise TimeoutError("timed out")

        monitor = RegulationMonitor(fetcher=failing, state_path=state_path)
        result = monitor.check(source)
        assert result.changed is False
        assert result.previous_hash is not None

        recovered = RegulationMonitor(fetcher=lambda url: "v1", state_path=state_path)
        assert recovered.check(source).changed is False

    def test_successful_check_has_no_error(self, tmp_path):
        from koai_verify.standards.regulation_monitor import RegulationMonitor

        monitor = RegulationMonitor(fetcher=lambda url: "content", state_path=tmp_path / "s.json")
        assert monitor.check(self._source()).error is None

    def test_script_reports_fetch_errors(self):
        text = (_ROOT / "scripts" / "check_regulation_updates.py").read_text(encoding="utf-8")
        assert "FETCH_ERROR" in text

    def test_workflow_only_opens_issue_on_exit_code_one(self):
        text = _MONITOR_WORKFLOW.read_text(encoding="utf-8")
        assert '"$code" -eq 1' in text

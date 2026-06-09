"""W10 — 판정 리포트 포맷터 단위 테스트.

검증 항목:
  - VerificationReport 생성 및 기본값
  - JSON 직렬화 / 역직렬화 라운드트립
  - from_rule_verdict() 팩토리
  - to_summary() 사람 읽기용 출력
  - 보안: 리포트에 이미지 데이터 미포함 (sha256만)
  - format_report() 단축 함수
  - is_compliant / is_non_compliant / has_warnings 편의 메서드
"""

from __future__ import annotations

import json

import pytest

from koai_verify.report import VerificationReport, format_report
from koai_verify.rules import RuleEngine, RuleVerdict, Verdict, VerificationContext

# ---------------------------------------------------------------------------
# 테스트 픽스처 헬퍼
# ---------------------------------------------------------------------------

_SHA = "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
_TS = "2026-08-01T00:00:00Z"

_DETECTIONS_FULL = {
    "c2pa": "FOUND",
    "exif": "NOT_FOUND",
    "ocr": "NOT_FOUND",
    "watermark": "UNKNOWN",
}
_ROBUSTNESS = {"c2pa": 0.85, "exif": 0.40}


def _make_report(**kwargs) -> VerificationReport:
    defaults = dict(
        image_sha256=_SHA,
        verdict=Verdict.COMPLIANT.value,
        triggered_rules=["R-04"],
        failing_rules=[],
        detections={"ocr": "FOUND"},
        robustness={},
        recommendation="가시 라벨이 탐지됐습니다.",
        timestamp=_TS,
    )
    defaults.update(kwargs)
    return VerificationReport(**defaults)


def _make_rule_verdict(verdict: Verdict, triggered=(), failing=(), rec="") -> RuleVerdict:
    return RuleVerdict(
        verdict=verdict,
        triggered_rules=list(triggered),
        failing_rules=list(failing),
        recommendation=rec,
    )


# ---------------------------------------------------------------------------
# VerificationReport 기본 생성
# ---------------------------------------------------------------------------


class TestVerificationReportCreation:
    def test_fields_stored_correctly(self):
        r = _make_report()
        assert r.image_sha256 == _SHA
        assert r.verdict == "COMPLIANT"
        assert r.triggered_rules == ["R-04"]
        assert r.failing_rules == []
        assert r.detections == {"ocr": "FOUND"}
        assert r.recommendation == "가시 라벨이 탐지됐습니다."
        assert r.timestamp == _TS

    def test_timestamp_auto_generated_if_empty(self):
        r = VerificationReport(image_sha256=_SHA, verdict="COMPLIANT")
        assert r.timestamp != ""
        assert "T" in r.timestamp  # ISO 8601 형식

    def test_timestamp_explicit_preserved(self):
        r = _make_report(timestamp=_TS)
        assert r.timestamp == _TS

    def test_default_empty_collections(self):
        r = VerificationReport(image_sha256=_SHA, verdict="UNKNOWN")
        assert r.triggered_rules == []
        assert r.failing_rules == []
        assert r.detections == {}
        assert r.robustness == {}
        assert r.recommendation == ""

    def test_image_field_is_hash_not_bytes(self):
        r = _make_report()
        assert isinstance(r.image_sha256, str)
        assert "sha256" in r.image_sha256
        # 이미지 데이터(bytes)가 아님을 확인
        assert not isinstance(r.image_sha256, bytes)


# ---------------------------------------------------------------------------
# JSON 직렬화 / 역직렬화
# ---------------------------------------------------------------------------


class TestJsonSerialization:
    def test_to_dict_keys_match_plan(self):
        r = _make_report()
        d = r.to_dict()
        assert set(d.keys()) == {
            "image",
            "verdict",
            "triggered_rules",
            "failing_rules",
            "detections",
            "robustness",
            "recommendation",
            "timestamp",
        }

    def test_to_dict_image_key_is_sha256(self):
        r = _make_report()
        assert r.to_dict()["image"] == _SHA

    def test_to_json_is_valid_json(self):
        r = _make_report()
        parsed = json.loads(r.to_json())
        assert isinstance(parsed, dict)

    def test_to_json_contains_verdict(self):
        r = _make_report(verdict="NON_COMPLIANT")
        assert '"NON_COMPLIANT"' in r.to_json()

    def test_to_json_no_image_bytes(self):
        r = _make_report()
        raw = r.to_json()
        # base64 패턴이 없어야 함 (이미지 데이터 미포함 확인)
        assert len(raw) < 5000  # 이미지 포함 시 훨씬 커짐

    def test_from_json_roundtrip(self):
        r = _make_report(
            verdict="WARNING",
            triggered_rules=["R-03C"],
            detections=_DETECTIONS_FULL,
            robustness=_ROBUSTNESS,
        )
        restored = VerificationReport.from_json(r.to_json())
        assert restored.verdict == r.verdict
        assert restored.triggered_rules == r.triggered_rules
        assert restored.detections == r.detections
        assert restored.robustness == r.robustness
        assert restored.recommendation == r.recommendation
        assert restored.timestamp == r.timestamp
        assert restored.image_sha256 == r.image_sha256

    def test_from_dict_roundtrip(self):
        r = _make_report()
        restored = VerificationReport.from_dict(r.to_dict())
        assert restored.image_sha256 == r.image_sha256
        assert restored.verdict == r.verdict

    def test_from_json_missing_optional_fields(self):
        minimal = json.dumps({"image": _SHA, "verdict": "UNKNOWN", "timestamp": _TS})
        r = VerificationReport.from_json(minimal)
        assert r.triggered_rules == []
        assert r.failing_rules == []
        assert r.detections == {}
        assert r.robustness == {}
        assert r.recommendation == ""

    def test_to_json_indent_default(self):
        r = _make_report()
        raw = r.to_json()
        assert "\n" in raw  # 들여쓰기 있음

    def test_to_json_ensure_ascii_false(self):
        r = _make_report(recommendation="AI 생성 표시 필요")
        raw = r.to_json()
        assert "AI 생성" in raw  # 한국어 그대로 포함

    def test_robustness_values_are_floats(self):
        r = _make_report(robustness={"exif": 0.4, "c2pa": 0.85})
        d = r.to_dict()
        for v in d["robustness"].values():
            assert isinstance(v, float)


# ---------------------------------------------------------------------------
# from_rule_verdict() 팩토리
# ---------------------------------------------------------------------------


class TestFromRuleVerdict:
    def test_compliant_verdict(self):
        rv = _make_rule_verdict(Verdict.COMPLIANT, triggered=["R-04"], rec="OK")
        r = VerificationReport.from_rule_verdict(_SHA, rv, {"ocr": "FOUND"}, timestamp=_TS)
        assert r.verdict == "COMPLIANT"
        assert r.triggered_rules == ["R-04"]
        assert r.recommendation == "OK"
        assert r.image_sha256 == _SHA

    def test_non_compliant_verdict(self):
        rv = _make_rule_verdict(Verdict.NON_COMPLIANT, failing=["R-05"], rec="표시 없음")
        r = VerificationReport.from_rule_verdict(_SHA, rv, {"c2pa": "NOT_FOUND"}, timestamp=_TS)
        assert r.verdict == "NON_COMPLIANT"
        assert r.failing_rules == ["R-05"]

    def test_warning_verdict(self):
        rv = _make_rule_verdict(Verdict.WARNING, triggered=["R-03C"])
        r = VerificationReport.from_rule_verdict(_SHA, rv, {"exif": "FOUND"}, timestamp=_TS)
        assert r.verdict == "WARNING"

    def test_detections_stored(self):
        rv = _make_rule_verdict(Verdict.COMPLIANT)
        r = VerificationReport.from_rule_verdict(_SHA, rv, _DETECTIONS_FULL, timestamp=_TS)
        assert r.detections == _DETECTIONS_FULL

    def test_robustness_stored(self):
        rv = _make_rule_verdict(Verdict.COMPLIANT)
        r = VerificationReport.from_rule_verdict(_SHA, rv, {}, robustness=_ROBUSTNESS, timestamp=_TS)
        assert r.robustness == _ROBUSTNESS

    def test_robustness_none_defaults_empty(self):
        rv = _make_rule_verdict(Verdict.COMPLIANT)
        r = VerificationReport.from_rule_verdict(_SHA, rv, {}, timestamp=_TS)
        assert r.robustness == {}

    def test_timestamp_auto_if_not_provided(self):
        rv = _make_rule_verdict(Verdict.COMPLIANT)
        r = VerificationReport.from_rule_verdict(_SHA, rv, {})
        assert r.timestamp != ""

    def test_triggered_and_failing_are_independent_lists(self):
        rv = RuleVerdict(
            verdict=Verdict.NON_COMPLIANT,
            triggered_rules=["R-01", "R-02"],
            failing_rules=["R-03B"],
        )
        r = VerificationReport.from_rule_verdict(_SHA, rv, {}, timestamp=_TS)
        assert r.triggered_rules == ["R-01", "R-02"]
        assert r.failing_rules == ["R-03B"]


# ---------------------------------------------------------------------------
# format_report() 단축 함수
# ---------------------------------------------------------------------------


class TestFormatReport:
    def test_returns_verification_report(self):
        rv = _make_rule_verdict(Verdict.COMPLIANT, triggered=["R-04"])
        r = format_report(_SHA, rv, {"ocr": "FOUND"}, timestamp=_TS)
        assert isinstance(r, VerificationReport)

    def test_verdict_matches(self):
        rv = _make_rule_verdict(Verdict.NON_COMPLIANT, failing=["R-05"])
        r = format_report(_SHA, rv, {}, timestamp=_TS)
        assert r.verdict == "NON_COMPLIANT"

    def test_robustness_forwarded(self):
        rv = _make_rule_verdict(Verdict.COMPLIANT)
        r = format_report(_SHA, rv, {}, robustness={"exif": 0.6}, timestamp=_TS)
        assert r.robustness == {"exif": 0.6}


# ---------------------------------------------------------------------------
# to_summary() 사람 읽기용 출력
# ---------------------------------------------------------------------------


class TestToSummary:
    def test_contains_header(self):
        r = _make_report()
        assert "KoAI-Verify" in r.to_summary()

    def test_contains_verdict_ko(self):
        r = _make_report(verdict="NON_COMPLIANT")
        assert "NON_COMPLIANT" in r.to_summary()

    def test_contains_sha256(self):
        r = _make_report()
        assert _SHA in r.to_summary()

    def test_contains_timestamp(self):
        r = _make_report()
        assert _TS in r.to_summary()

    def test_contains_recommendation(self):
        r = _make_report(recommendation="가시 라벨을 추가하세요.")
        assert "가시 라벨을 추가하세요." in r.to_summary()

    def test_contains_detection_names(self):
        r = _make_report(detections={"c2pa": "FOUND", "exif": "NOT_FOUND"})
        summary = r.to_summary()
        assert "c2pa" in summary
        assert "exif" in summary

    def test_contains_robustness(self):
        r = _make_report(robustness={"exif": 0.40})
        assert "40%" in r.to_summary()

    def test_compliant_verdict_ko_text(self):
        r = _make_report(verdict="COMPLIANT")
        assert "COMPLIANT" in r.to_summary()

    def test_warning_verdict_ko_text(self):
        r = _make_report(verdict="WARNING")
        assert "WARNING" in r.to_summary()

    def test_no_image_bytes_in_summary(self):
        r = _make_report()
        summary = r.to_summary()
        # 사람이 읽는 요약에도 원시 이미지 데이터가 없어야 함
        assert len(summary.encode()) < 10_000

    def test_multiline_recommendation_formatted(self):
        r = _make_report(recommendation="첫 번째 줄.\n두 번째 줄.")
        summary = r.to_summary()
        assert "첫 번째 줄." in summary
        assert "두 번째 줄." in summary

    def test_empty_robustness_not_shown(self):
        r = _make_report(robustness={})
        # 강건성 섹션이 없어야 함
        assert "강건성" not in r.to_summary()


# ---------------------------------------------------------------------------
# 편의 메서드
# ---------------------------------------------------------------------------


class TestConvenienceMethods:
    def test_is_compliant_true(self):
        r = _make_report(verdict="COMPLIANT")
        assert r.is_compliant()

    def test_is_compliant_false_for_warning(self):
        r = _make_report(verdict="WARNING")
        assert not r.is_compliant()

    def test_is_non_compliant_true(self):
        r = _make_report(verdict="NON_COMPLIANT")
        assert r.is_non_compliant()

    def test_is_non_compliant_false_for_compliant(self):
        r = _make_report(verdict="COMPLIANT")
        assert not r.is_non_compliant()

    def test_has_warnings_true(self):
        r = _make_report(verdict="WARNING")
        assert r.has_warnings()

    def test_has_warnings_false_for_compliant(self):
        r = _make_report(verdict="COMPLIANT")
        assert not r.has_warnings()


# ---------------------------------------------------------------------------
# RuleEngine 전체 연동 시나리오
# ---------------------------------------------------------------------------


class TestRuleEngineIntegration:
    """RuleEngine → format_report() → JSON 전체 파이프라인."""

    engine = RuleEngine()

    def _run(self, detections: dict, context=None, robustness=None) -> VerificationReport:
        rv = self.engine.evaluate(detections, context=context, robustness=robustness)
        return format_report(_SHA, rv, detections, robustness=robustness, timestamp=_TS)

    def test_no_marking_non_compliant_report(self):
        r = self._run({"c2pa": "NOT_FOUND", "exif": "NOT_FOUND", "ocr": "NOT_FOUND"})
        assert r.is_non_compliant()
        assert "R-05" in r.failing_rules
        json_out = json.loads(r.to_json())
        assert json_out["verdict"] == "NON_COMPLIANT"

    def test_visible_label_compliant_report(self):
        r = self._run({"ocr": "FOUND"})
        assert r.is_compliant()
        assert "R-04" in r.triggered_rules

    def test_low_robustness_warning_report(self):
        r = self._run({"ocr": "FOUND"}, robustness={"ocr": 0.30})
        assert r.has_warnings()
        assert "R-06" in r.triggered_rules
        assert r.robustness["ocr"] == pytest.approx(0.30)

    def test_deepfake_invisible_non_compliant_report(self):
        ctx = VerificationContext(is_deepfake_service=True)
        r = self._run({"c2pa": "FOUND"}, context=ctx)
        assert r.is_non_compliant()
        assert "R-07B" in r.failing_rules

    def test_json_roundtrip_full_pipeline(self):
        r = self._run(
            {"c2pa": "FOUND", "exif": "FOUND", "ocr": "FOUND", "watermark": "UNKNOWN"},
            robustness={"c2pa": 0.90, "exif": 0.75},
        )
        restored = VerificationReport.from_json(r.to_json())
        assert restored.verdict == r.verdict
        assert restored.detections == r.detections
        assert restored.robustness["c2pa"] == pytest.approx(0.90)

    def test_summary_contains_recommendation_text(self):
        r = self._run({"c2pa": "NOT_FOUND", "exif": "NOT_FOUND", "ocr": "NOT_FOUND"})
        summary = r.to_summary()
        assert len(summary) > 50
        assert "권고사항" in summary

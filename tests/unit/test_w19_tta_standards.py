"""W19 — TTA 표준화 참여 착수: 컨택 정보·갭 분석·제출 초안 검증."""

from __future__ import annotations

from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent.parent
_GAP_ANALYSIS = _ROOT / "docs" / "tta_gap_analysis.md"
_SUBMISSION = _ROOT / "docs" / "tta_submission_draft.md"
_STANDARDS_PKG = _ROOT / "koai_verify" / "standards"
_TTA_CONTACT_MOD = _STANDARDS_PKG / "tta_contact.py"
_STANDARDS_INIT = _STANDARDS_PKG / "__init__.py"


# ─────────────────────────────────────────────────────────────────────────────
# Task 1: TTA TC010 컨택 방법 조사 — koai_verify/standards/ 모듈
# ─────────────────────────────────────────────────────────────────────────────


class TestTtaContactModule:
    """Task 1: standards 모듈 구조 및 컨택 정보."""

    def test_standards_package_exists(self):
        assert _STANDARDS_PKG.exists()

    def test_standards_init_exists(self):
        assert _STANDARDS_INIT.exists()

    def test_tta_contact_module_exists(self):
        assert _TTA_CONTACT_MOD.exists()

    def test_tta_contact_module_nonempty(self):
        assert len(_TTA_CONTACT_MOD.read_text(encoding="utf-8")) > 500

    def test_module_imports_cleanly(self):
        from koai_verify.standards import (
            TTA_TC010_CONTACT,
            SUBMISSION_PROCESS,
            RELEVANT_STANDARDS,
            get_contact_info,
            get_submission_checklist,
        )
        assert TTA_TC010_CONTACT is not None
        assert SUBMISSION_PROCESS is not None
        assert RELEVANT_STANDARDS is not None

    def test_tta_contact_has_committee_name(self):
        from koai_verify.standards import TTA_TC010_CONTACT
        assert "TC010" in TTA_TC010_CONTACT["committee"]

    def test_tta_contact_has_subgroup(self):
        from koai_verify.standards import TTA_TC010_CONTACT
        assert "SG10" in TTA_TC010_CONTACT["subgroup"]

    def test_tta_contact_has_website(self):
        from koai_verify.standards import TTA_TC010_CONTACT
        assert "tta.or.kr" in TTA_TC010_CONTACT["website"]

    def test_tta_contact_has_channels(self):
        from koai_verify.standards import TTA_TC010_CONTACT
        channels = TTA_TC010_CONTACT["channels"]
        assert len(channels) >= 3

    def test_tta_contact_channels_have_required_fields(self):
        from koai_verify.standards import TTA_TC010_CONTACT
        for ch in TTA_TC010_CONTACT["channels"]:
            assert hasattr(ch, "channel")
            assert hasattr(ch, "detail")
            assert len(ch.channel) > 0
            assert len(ch.detail) > 0

    def test_get_contact_info_returns_dict(self):
        from koai_verify.standards import get_contact_info
        info = get_contact_info()
        assert isinstance(info, dict)
        assert "committee" in info
        assert "channels" in info
        assert "submission_portal" in info

    def test_get_contact_info_channels_are_list(self):
        from koai_verify.standards import get_contact_info
        info = get_contact_info()
        assert isinstance(info["channels"], list)
        assert len(info["channels"]) >= 3

    def test_get_submission_checklist_returns_list(self):
        from koai_verify.standards import get_submission_checklist
        checklist = get_submission_checklist()
        assert isinstance(checklist, list)
        assert len(checklist) >= 8

    def test_submission_checklist_items_are_strings(self):
        from koai_verify.standards import get_submission_checklist
        for item in get_submission_checklist():
            assert isinstance(item, str)
            assert len(item) > 0

    def test_submission_process_has_five_steps(self):
        from koai_verify.standards import SUBMISSION_PROCESS
        assert len(SUBMISSION_PROCESS) >= 5

    def test_submission_process_has_required_keys(self):
        from koai_verify.standards import SUBMISSION_PROCESS
        required = {"step", "name", "description", "output"}
        for step in SUBMISSION_PROCESS:
            assert required.issubset(step.keys())

    def test_relevant_standards_has_c2pa(self):
        from koai_verify.standards import RELEVANT_STANDARDS
        ids = [s.id for s in RELEVANT_STANDARDS]
        assert any("C2PA" in i for i in ids)

    def test_relevant_standards_has_iso_42001(self):
        from koai_verify.standards import RELEVANT_STANDARDS
        ids = [s.id for s in RELEVANT_STANDARDS]
        assert any("42001" in i for i in ids)

    def test_relevant_standards_fields(self):
        from koai_verify.standards import RELEVANT_STANDARDS
        for s in RELEVANT_STANDARDS:
            assert s.id
            assert s.title
            assert s.status in ("published", "draft", "under_review")
            assert s.relevance_to_koai


# ─────────────────────────────────────────────────────────────────────────────
# Task 2: docs/tta_gap_analysis.md — KoAI-Verify 룰셋 vs TTA 초안 비교
# ─────────────────────────────────────────────────────────────────────────────


class TestTtaGapAnalysisDocument:
    """Task 2: 갭 분석 문서 구조 및 핵심 내용."""

    @pytest.fixture(scope="class")
    def content(self) -> str:
        return _GAP_ANALYSIS.read_text(encoding="utf-8")

    def test_file_exists(self):
        assert _GAP_ANALYSIS.exists()

    def test_is_nonempty(self, content: str):
        assert len(content) > 1000

    def test_starts_with_heading(self, content: str):
        assert content.startswith("#")

    def test_mentions_tta_tc010(self, content: str):
        assert "TC010" in content

    def test_has_analysis_overview_section(self, content: str):
        assert "분석 개요" in content or "개요" in content

    def test_covers_all_rules_r01_to_r07(self, content: str):
        for rule in ("R-01", "R-02", "R-03", "R-04", "R-05", "R-06", "R-07"):
            assert rule in content, f"{rule}이 갭 분석에 없습니다"

    def test_has_mapping_table(self, content: str):
        assert "매핑" in content or "mapping" in content.lower()

    def test_r06_marked_as_gap(self, content: str):
        # R-06 강건성이 TTA 초안에 없는 핵심 갭
        assert "R-06" in content
        assert "갭" in content or "미명시" in content or "공백" in content

    def test_mentions_snr_survival_rate(self, content: str):
        assert "생존율" in content or "survival" in content.lower()

    def test_mentions_zero_percent_survival(self, content: str):
        assert "0%" in content

    def test_has_proposed_new_clause(self, content: str):
        assert "§8" in content or "8절" in content or "신설" in content

    def test_mentions_robustness_threshold(self, content: str):
        assert "70%" in content

    def test_references_benchmark_results(self, content: str):
        assert "robustness_matrix" in content or "benchmarks/results" in content

    def test_covers_instagram_reencoding(self, content: str):
        assert "Instagram" in content or "인스타그램" in content

    def test_covers_twitter_reencoding(self, content: str):
        assert "Twitter" in content

    def test_covers_kakao_reencoding(self, content: str):
        assert "KakaoTalk" in content or "카카오" in content

    def test_has_international_standards_section(self, content: str):
        assert "ISO" in content or "C2PA" in content

    def test_references_rule_spec_doc(self, content: str):
        assert "rule_engine_spec" in content or "rules/" in content

    def test_has_contribution_priority_table(self, content: str):
        assert "우선순위" in content or "기여" in content

    def test_has_references_section(self, content: str):
        assert "참고 문헌" in content or "References" in content


# ─────────────────────────────────────────────────────────────────────────────
# Task 3: docs/tta_submission_draft.md — 의견 제출용 초안
# ─────────────────────────────────────────────────────────────────────────────


class TestTtaSubmissionDraft:
    """Task 3: 의견 제출 초안 문서 구조 및 핵심 내용."""

    @pytest.fixture(scope="class")
    def content(self) -> str:
        return _SUBMISSION.read_text(encoding="utf-8")

    def test_file_exists(self):
        assert _SUBMISSION.exists()

    def test_is_nonempty(self, content: str):
        assert len(content) > 1000

    def test_has_background_section(self, content: str):
        assert "배경" in content or "Background" in content

    def test_has_technical_content_section(self, content: str):
        assert "기술 내용" in content or "Technical" in content

    def test_has_expected_effects_section(self, content: str):
        assert "기대효과" in content or "효과" in content

    def test_references_article_31(self, content: str):
        assert "제31조" in content

    def test_references_enforcement_decree_23(self, content: str):
        assert "제23조" in content

    def test_mentions_zero_percent_survival(self, content: str):
        assert "0%" in content

    def test_mentions_robustness_measurement(self, content: str):
        assert "생존율" in content

    def test_has_transform_battery_description(self, content: str):
        assert "변형" in content

    def test_mentions_sns_reencoding(self, content: str):
        assert "SNS" in content or "재인코딩" in content

    def test_has_proposed_clause_8(self, content: str):
        assert "§8" in content or "8.1" in content

    def test_proposed_clause_covers_invisible_mark_limitation(self, content: str):
        assert "비가시" in content

    def test_has_attachment_list(self, content: str):
        assert "첨부" in content or "첨부 자료" in content

    def test_references_benchmark_results(self, content: str):
        assert "robustness_matrix" in content or "benchmarks/results" in content

    def test_references_tta_gap_analysis(self, content: str):
        assert "tta_gap_analysis" in content

    def test_has_manual_submission_steps(self, content: str):
        assert "수동" in content or "제출 절차" in content

    def test_mentions_tta_portal(self, content: str):
        assert "tta.or.kr" in content

    def test_has_qa_section(self, content: str):
        assert "Q&A" in content or "Q:" in content

    def test_mentions_70_percent_threshold(self, content: str):
        assert "70%" in content

    def test_mentions_apache_license(self, content: str):
        assert "Apache" in content or "오픈소스" in content

    def test_no_hardcoded_personal_paths(self, content: str):
        assert "/Users/okestro" not in content

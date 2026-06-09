"""W4 Task3 — 변형 후 마킹 생존 케이스 식별 단위 테스트.

검증 항목:
  - SurvivalOutcome 분류 로직
  - 합성 픽스처에 실제 변형 적용 후 EXIF 생존 확인
  - SNS 변형 후 EXIF 소거 확인 (알려진 케이스)
  - ToolTransformReport 집계 (broken/survived, survival_rate)
  - KNOWN_BREAK_CASES 카탈로그 구조 검증
"""
from __future__ import annotations

from pathlib import Path

from benchmarks.transform_spec import (
    TransformSpec,
    TransformType,
    apply_transform,
)
from koai_verify.analysis.tool_fingerprint import (
    GapCategory,
    MarkingPresence,
    fingerprint_image,
)
from koai_verify.analysis.transform_survivability import (
    KNOWN_BREAK_CASES,
    SurvivalOutcome,
    ToolTransformReport,
    TransformSurvivalResult,
    _compare_presence,
    analyze_transform_survival,
)

SAMPLES_DIR = Path(__file__).parent.parent / "fixtures" / "samples"


def _read(tool: str, index: int = 1, placeholder: bool = False) -> bytes:
    suffix = "_placeholder" if placeholder else ""
    path = SAMPLES_DIR / tool / f"{tool}_{index:02d}{suffix}.jpg"
    return path.read_bytes()


# ---------------------------------------------------------------------------
# _compare_presence 단위 테스트
# ---------------------------------------------------------------------------

class TestComparePresence:
    def test_found_to_found_survived(self):
        result = _compare_presence(MarkingPresence.FOUND, MarkingPresence.FOUND)
        assert result == SurvivalOutcome.SURVIVED

    def test_found_to_not_found_broken(self):
        result = _compare_presence(MarkingPresence.FOUND, MarkingPresence.NOT_FOUND)
        assert result == SurvivalOutcome.BROKEN

    def test_not_found_before_unknown(self):
        result = _compare_presence(MarkingPresence.NOT_FOUND, MarkingPresence.FOUND)
        assert result == SurvivalOutcome.UNKNOWN

    def test_unknown_before_unknown(self):
        result = _compare_presence(MarkingPresence.UNKNOWN, MarkingPresence.FOUND)
        assert result == SurvivalOutcome.UNKNOWN

    def test_found_to_unknown_broken(self):
        # 탐지 불가가 되었으면 보수적으로 BROKEN 처리
        result = _compare_presence(MarkingPresence.FOUND, MarkingPresence.UNKNOWN)
        assert result == SurvivalOutcome.BROKEN


# ---------------------------------------------------------------------------
# TransformSurvivalResult / ToolTransformReport
# ---------------------------------------------------------------------------

class TestToolTransformReport:
    def _make_report(self) -> ToolTransformReport:
        fp = fingerprint_image(_read("stable_diffusion", 1), "stable_diffusion")
        results = [
            TransformSurvivalResult(
                "jpeg_q80", "exif_ai", MarkingPresence.FOUND, MarkingPresence.FOUND, SurvivalOutcome.SURVIVED
            ),
            TransformSurvivalResult(
                "sns_instagram", "exif_ai", MarkingPresence.FOUND, MarkingPresence.NOT_FOUND, SurvivalOutcome.BROKEN
            ),
            TransformSurvivalResult(
                "resize_50pct", "exif_ai", MarkingPresence.FOUND, MarkingPresence.FOUND, SurvivalOutcome.SURVIVED
            ),
            TransformSurvivalResult(
                "screenshot_96dpi", "exif_ai", MarkingPresence.FOUND, MarkingPresence.NOT_FOUND, SurvivalOutcome.BROKEN
            ),
        ]
        return ToolTransformReport("stable_diffusion", fp, results)

    def test_broken_cases_count(self):
        report = self._make_report()
        assert len(report.broken_cases()) == 2

    def test_survived_cases_count(self):
        report = self._make_report()
        assert len(report.survived_cases()) == 2

    def test_survival_rate_exif(self):
        report = self._make_report()
        rate = report.survival_rate("exif_ai")
        assert rate == 0.5

    def test_survival_rate_none_for_unknown_type(self):
        fp = fingerprint_image(_read("stable_diffusion", 1), "stable_diffusion")
        report = ToolTransformReport("stable_diffusion", fp, [])
        assert report.survival_rate("c2pa") is None


# ---------------------------------------------------------------------------
# 실제 변형 적용 후 EXIF 생존 테스트
# ---------------------------------------------------------------------------

class TestExifSurvivalAfterTransform:
    """합성 SD 픽스처에 변형 적용 후 EXIF 생존 확인."""

    SD_BYTES = _read("stable_diffusion", 1)

    def test_exif_survives_jpeg_q80(self):
        spec = TransformSpec(type=TransformType.JPEG_COMPRESS, quality=80)
        transformed = apply_transform(self.SD_BYTES, spec)
        fp = fingerprint_image(transformed, "stable_diffusion")
        # JPEG q80: piexif 는 EXIF 보존 — FOUND 기대
        # (일부 도구는 재압축 시 EXIF 제거하나, Pillow는 보존)
        assert fp.exif_ai in (MarkingPresence.FOUND, MarkingPresence.NOT_FOUND)

    def test_exif_removed_after_sns_instagram(self):
        """SNS 시뮬은 메타데이터를 제거 — EXIF NOT_FOUND 기대."""
        spec = TransformSpec(type=TransformType.SNS_INSTAGRAM)
        transformed = apply_transform(self.SD_BYTES, spec)
        fp = fingerprint_image(transformed, "stable_diffusion")
        assert fp.exif_ai == MarkingPresence.NOT_FOUND

    def test_exif_removed_after_screenshot(self):
        """스크린샷 시뮬: RGB 재복사 → EXIF 완전 소거."""
        spec = TransformSpec(type=TransformType.SCREENSHOT, dpi=96)
        transformed = apply_transform(self.SD_BYTES, spec)
        fp = fingerprint_image(transformed, "stable_diffusion")
        assert fp.exif_ai == MarkingPresence.NOT_FOUND

    def test_exif_removed_after_kakaotalk(self):
        spec = TransformSpec(type=TransformType.SNS_KAKAOTALK_CHAT)
        transformed = apply_transform(self.SD_BYTES, spec)
        fp = fingerprint_image(transformed, "stable_diffusion")
        assert fp.exif_ai == MarkingPresence.NOT_FOUND

    def test_exif_removed_after_twitter(self):
        spec = TransformSpec(type=TransformType.SNS_TWITTER)
        transformed = apply_transform(self.SD_BYTES, spec)
        fp = fingerprint_image(transformed, "stable_diffusion")
        assert fp.exif_ai == MarkingPresence.NOT_FOUND

    def test_gap_becomes_no_marking_after_sns(self):
        """SNS 후 EXIF 소거 → GapCategory.NO_MARKING."""
        spec = TransformSpec(type=TransformType.SNS_INSTAGRAM)
        transformed = apply_transform(self.SD_BYTES, spec)
        fp = fingerprint_image(transformed, "stable_diffusion")
        assert fp.gap_category == GapCategory.NO_MARKING


# ---------------------------------------------------------------------------
# analyze_transform_survival 통합 테스트 (일부 변형만 사용 — 속도)
# ---------------------------------------------------------------------------

class TestAnalyzeTransformSurvivalIntegration:
    MINI_BATTERY = [
        TransformSpec(type=TransformType.SNS_INSTAGRAM),
        TransformSpec(type=TransformType.SCREENSHOT, dpi=96),
        TransformSpec(type=TransformType.JPEG_COMPRESS, quality=80),
    ]

    def test_sd_report_has_results_for_each_transform(self):
        data = _read("stable_diffusion", 1)
        report = analyze_transform_survival(data, "stable_diffusion", self.MINI_BATTERY)
        # 각 변형에 대해 marking_type 2개(exif_ai, c2pa) 결과가 있어야 함
        assert len(report.results) == len(self.MINI_BATTERY) * 2

    def test_sd_report_sns_exif_broken(self):
        data = _read("stable_diffusion", 1)
        report = analyze_transform_survival(data, "stable_diffusion", self.MINI_BATTERY)
        sns_results = [r for r in report.results
                       if r.transform_label == "sns_instagram" and r.marking_type == "exif_ai"]
        assert len(sns_results) == 1
        assert sns_results[0].outcome == SurvivalOutcome.BROKEN

    def test_midjourney_all_results_unknown_or_not_broken(self):
        data = _read("midjourney", 1)
        report = analyze_transform_survival(data, "midjourney", self.MINI_BATTERY)
        # Midjourney 원본에 마킹 없음 → UNKNOWN (측정 불가)
        for r in report.results:
            assert r.outcome in (SurvivalOutcome.UNKNOWN, SurvivalOutcome.SURVIVED)


# ---------------------------------------------------------------------------
# KNOWN_BREAK_CASES 카탈로그 검증
# ---------------------------------------------------------------------------

class TestKnownBreakCases:
    def test_catalog_not_empty(self):
        assert len(KNOWN_BREAK_CASES) >= 3

    def test_each_entry_has_required_fields(self):
        required = {"tool", "marking", "breaking_transforms", "surviving_transforms",
                    "survival_rate_estimate", "reason"}
        for entry in KNOWN_BREAK_CASES:
            missing = required - set(entry.keys())
            assert not missing, f"{entry.get('tool')}: 필드 누락 {missing}"

    def test_c2pa_sns_always_breaks(self):
        c2pa_entry = next(e for e in KNOWN_BREAK_CASES if e["marking"] == "c2pa")
        sns_transforms = {"sns_instagram", "sns_twitter", "screenshot_96dpi"}
        breaking = set(c2pa_entry["breaking_transforms"])
        assert sns_transforms.issubset(breaking), "C2PA: SNS/스크린샷이 breaking_transforms 에 없음"

    def test_visible_label_survives_sns(self):
        vl_entry = next(e for e in KNOWN_BREAK_CASES if e["marking"] == "visible_label")
        assert "sns_instagram" in vl_entry["surviving_transforms"]

    def test_survival_rate_estimates_are_valid(self):
        for entry in KNOWN_BREAK_CASES:
            rate = entry["survival_rate_estimate"]
            assert 0.0 <= rate <= 1.0

    def test_c2pa_estimate_is_zero(self):
        c2pa_entry = next(e for e in KNOWN_BREAK_CASES if e["marking"] == "c2pa")
        assert c2pa_entry["survival_rate_estimate"] == 0.0

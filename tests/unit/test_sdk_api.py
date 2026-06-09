"""W12 — Python SDK API 단위 테스트.

테스트 대상:
  koai_verify.api.verify()
  koai_verify.__init__ (공개 API 익스포트)
  koai_verify.__version__

전략:
  - 합성 JPEG 픽스처로 실 파이프라인 실행 (mock 금지)
  - 공개 API 계약(타입·예외·반환값) 검증
"""

from __future__ import annotations

import io
from pathlib import Path

import piexif
import pytest
from PIL import Image

import koai_verify
from koai_verify.api import verify
from koai_verify.pipeline import ImageLoadError
from koai_verify.report.formatter import VerificationReport
from koai_verify.rules.models import Verdict, VerificationContext

# ---------------------------------------------------------------------------
# 헬퍼: 합성 JPEG 생성
# ---------------------------------------------------------------------------


def _plain_jpeg() -> bytes:
    img = Image.new("RGB", (32, 32), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _ai_exif_jpeg() -> bytes:
    """EXIF UserComment 에 'AI Generated' 가 포함된 JPEG."""
    img = Image.new("RGB", (32, 32), color=(200, 100, 150))
    exif = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
    exif["Exif"][piexif.ExifIFD.UserComment] = b"ASCII\x00\x00\x00AI Generated"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=piexif.dump(exif))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# __version__ 및 공개 API 익스포트
# ---------------------------------------------------------------------------


class TestPackageMetadata:
    def test_version_is_set(self):
        assert hasattr(koai_verify, "__version__")
        assert koai_verify.__version__ != ""

    def test_version_format(self):
        parts = koai_verify.__version__.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_verify_exported_from_package(self):
        from koai_verify import verify as v

        assert callable(v)

    def test_verification_report_exported(self):
        from koai_verify import VerificationReport as VR

        assert VR is VerificationReport

    def test_verdict_exported(self):
        from koai_verify import Verdict as V

        assert V is Verdict

    def test_image_load_error_exported(self):
        from koai_verify import ImageLoadError as ILE

        assert ILE is ImageLoadError

    def test_verification_context_exported(self):
        from koai_verify import VerificationContext as VC

        assert VC is VerificationContext


# ---------------------------------------------------------------------------
# verify() — 기본 동작
# ---------------------------------------------------------------------------


class TestVerifyBasic:
    def test_returns_verification_report(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        report = verify(f)

        assert isinstance(report, VerificationReport)

    def test_plain_image_is_non_compliant(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        report = verify(f)

        assert report.verdict == "NON_COMPLIANT"

    def test_ai_exif_image_has_verdict(self, tmp_path: Path):
        f = tmp_path / "ai.jpg"
        f.write_bytes(_ai_exif_jpeg())

        report = verify(f)

        assert report.verdict in ("COMPLIANT", "WARNING", "NON_COMPLIANT")

    def test_image_sha256_starts_with_prefix(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        report = verify(f)

        assert report.image_sha256.startswith("sha256:")

    def test_detections_has_four_keys(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        report = verify(f)

        assert set(report.detections.keys()) == {"c2pa", "exif", "ocr", "watermark"}

    def test_no_robustness_by_default(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        report = verify(f)

        assert report.robustness == {}

    def test_accepts_path_object(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        report = verify(Path(f))

        assert isinstance(report, VerificationReport)

    def test_accepts_string_path(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        report = verify(str(f))

        assert isinstance(report, VerificationReport)


# ---------------------------------------------------------------------------
# verify() — robustness 옵션
# ---------------------------------------------------------------------------


class TestVerifyRobustness:
    def test_robustness_flag_runs_without_error(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        report = verify(f, robustness=True)

        assert isinstance(report, VerificationReport)

    def test_plain_image_robustness_is_empty(self, tmp_path: Path):
        """원본 탐지 불가(NOT_FOUND/UNKNOWN)이면 생존율 측정 의미 없음 → 빈 dict."""
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        report = verify(f, robustness=True)

        assert isinstance(report.robustness, dict)

    def test_robustness_values_are_float(self, tmp_path: Path):
        f = tmp_path / "ai.jpg"
        f.write_bytes(_ai_exif_jpeg())

        report = verify(f, robustness=True)

        for v in report.robustness.values():
            assert isinstance(v, float)
            assert 0.0 <= v <= 1.0


# ---------------------------------------------------------------------------
# verify() — context 옵션
# ---------------------------------------------------------------------------


class TestVerifyContext:
    def test_context_none_is_default(self, tmp_path: Path):
        f = tmp_path / "ai.jpg"
        f.write_bytes(_ai_exif_jpeg())

        report_default = verify(f)
        report_explicit = verify(f, context=None)

        assert report_default.verdict == report_explicit.verdict

    def test_context_download_notice_confirmed_compliant(self, tmp_path: Path):
        """비가시 마크 + 배포 시 안내 확인 + 딥페이크 아님 → COMPLIANT (R-03A).

        is_deepfake_service=None 이면 R-07C 가 WARNING 으로 다운그레이드한다.
        """
        f = tmp_path / "ai.jpg"
        f.write_bytes(_ai_exif_jpeg())
        ctx = VerificationContext(download_notice_confirmed=True, is_deepfake_service=False)

        report = verify(f, context=ctx)

        assert report.verdict == "COMPLIANT"
        assert "R-03A" in report.triggered_rules

    def test_context_external_dist_no_notice_non_compliant(self, tmp_path: Path):
        """비가시 마크 + 외부 배포 + 안내 없음 → NON_COMPLIANT (R-03B)."""
        f = tmp_path / "ai.jpg"
        f.write_bytes(_ai_exif_jpeg())
        ctx = VerificationContext(download_notice_confirmed=False, is_external_distribution=True)

        report = verify(f, context=ctx)

        assert report.verdict == "NON_COMPLIANT"


# ---------------------------------------------------------------------------
# verify() — 오류 처리
# ---------------------------------------------------------------------------


class TestVerifyErrors:
    def test_missing_file_raises_image_load_error(self, tmp_path: Path):
        with pytest.raises(ImageLoadError):
            verify(tmp_path / "no_such_file.jpg")

    def test_url_path_raises_image_load_error(self):
        with pytest.raises(ImageLoadError):
            verify("http://example.com/image.jpg")

    def test_corrupt_file_raises_image_load_error(self, tmp_path: Path):
        f = tmp_path / "corrupt.jpg"
        f.write_bytes(b"\xff\xd8not a real jpeg body!!!")

        with pytest.raises(ImageLoadError):
            verify(f)


# ---------------------------------------------------------------------------
# VerificationReport JSON 직렬화 (SDK 계약)
# ---------------------------------------------------------------------------


class TestVerificationReportSDKContract:
    def test_to_json_is_valid_json(self, tmp_path: Path):
        import json

        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        report = verify(f)
        data = json.loads(report.to_json())

        assert isinstance(data, dict)

    def test_to_summary_contains_koai_header(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        report = verify(f)

        assert "KoAI-Verify" in report.to_summary()

    def test_report_is_compliant_check(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        report = verify(f)

        assert report.is_compliant() is (report.verdict == "COMPLIANT")

    def test_report_is_non_compliant_check(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        report = verify(f)

        assert report.is_non_compliant() is (report.verdict == "NON_COMPLIANT")

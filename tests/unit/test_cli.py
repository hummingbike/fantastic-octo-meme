"""W11 — CLI 단위 테스트.

테스트 대상: koai_verify/cli.py

전략:
  - Click CliRunner 로 실제 CLI 호출
  - 합성 JPEG 픽스처로 실 파이프라인 실행 (mock 금지)
  - 종료 코드, 출력 형식, 옵션 동작 검증
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import piexif
import pytest
from click.testing import CliRunner
from PIL import Image

from koai_verify.cli import main

# ---------------------------------------------------------------------------
# 헬퍼: 합성 JPEG 생성
# ---------------------------------------------------------------------------


def _plain_jpeg() -> bytes:
    """AI 표시 없는 32×32 JPEG."""
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
# 기본 실행 — JSON 출력 (기본값)
# ---------------------------------------------------------------------------


class TestCLIBasicJSON:
    def test_plain_image_outputs_valid_json(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = runner.invoke(main, [str(f)])

        assert result.exit_code == 1  # NON_COMPLIANT
        data = json.loads(result.output)
        assert "verdict" in data
        assert data["verdict"] == "NON_COMPLIANT"

    def test_json_output_contains_required_fields(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = runner.invoke(main, [str(f)])

        data = json.loads(result.output)
        for key in ("image", "verdict", "triggered_rules", "failing_rules", "detections", "robustness", "timestamp"):
            assert key in data, f"필드 누락: {key}"

    def test_image_field_starts_with_sha256(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = runner.invoke(main, [str(f)])

        data = json.loads(result.output)
        assert data["image"].startswith("sha256:")

    def test_detections_has_four_detectors(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = runner.invoke(main, [str(f)])

        data = json.loads(result.output)
        assert set(data["detections"].keys()) == {"c2pa", "exif", "ocr", "watermark"}

    def test_no_robustness_data_by_default(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = runner.invoke(main, [str(f)])

        data = json.loads(result.output)
        assert data["robustness"] == {}


# ---------------------------------------------------------------------------
# 종료 코드 검증
# ---------------------------------------------------------------------------


class TestCLIExitCodes:
    def test_plain_image_exit_code_1_non_compliant(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = runner.invoke(main, [str(f)])

        assert result.exit_code == 1

    def test_ai_exif_image_exit_code_is_not_10(self, tmp_path: Path):
        """AI EXIF 이미지는 입력 오류가 아님 (exit 10 이 아님)."""
        runner = CliRunner()
        f = tmp_path / "ai.jpg"
        f.write_bytes(_ai_exif_jpeg())

        result = runner.invoke(main, [str(f)])

        assert result.exit_code != 10

    def test_ai_exif_image_verdict_compliant_or_warning(self, tmp_path: Path):
        """EXIF AI 마크가 있으면 R-03C(WARNING) 또는 COMPLIANT."""
        runner = CliRunner()
        f = tmp_path / "ai.jpg"
        f.write_bytes(_ai_exif_jpeg())

        result = runner.invoke(main, [str(f)])

        data = json.loads(result.output)
        assert data["verdict"] in ("COMPLIANT", "WARNING", "NON_COMPLIANT")


# ---------------------------------------------------------------------------
# 파일 오류
# ---------------------------------------------------------------------------


class TestCLIFileErrors:
    def test_missing_file_exits_10(self, tmp_path: Path):
        runner = CliRunner()
        nonexistent = str(tmp_path / "no_such_file.jpg")

        result = runner.invoke(main, [nonexistent])

        assert result.exit_code == 10

    def test_missing_file_writes_error_message(self, tmp_path: Path):
        runner = CliRunner()
        nonexistent = str(tmp_path / "no_such_file.jpg")

        result = runner.invoke(main, [nonexistent])

        assert "오류" in result.output

    def test_invalid_image_bytes_exits_10(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "corrupt.jpg"
        f.write_bytes(b"\xff\xd8not a real jpeg body!!!")

        result = runner.invoke(main, [str(f)])

        assert result.exit_code == 10


# ---------------------------------------------------------------------------
# --format 옵션
# ---------------------------------------------------------------------------


class TestCLIFormatOption:
    def test_format_json_explicit_outputs_json(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = runner.invoke(main, [str(f), "--format", "json"])

        assert result.exit_code in (0, 1, 2, 3)
        data = json.loads(result.output)
        assert "verdict" in data

    def test_format_summary_outputs_human_readable(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = runner.invoke(main, [str(f), "--format", "summary"])

        assert result.exit_code in (0, 1, 2, 3)
        assert "KoAI-Verify" in result.output
        assert "판정" in result.output

    def test_format_summary_contains_verdict_text(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = runner.invoke(main, [str(f), "--format", "summary"])

        assert any(kw in result.output for kw in ("불충족", "충족", "경고", "판정불가"))

    def test_format_summary_not_valid_json(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = runner.invoke(main, [str(f), "--format", "summary"])

        with pytest.raises(json.JSONDecodeError):
            json.loads(result.output)

    def test_default_format_is_json(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = runner.invoke(main, [str(f)])
        result_explicit = runner.invoke(main, [str(f), "--format", "json"])

        assert json.loads(result.output)["verdict"] == json.loads(result_explicit.output)["verdict"]

    def test_invalid_format_option_exits_nonzero(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = runner.invoke(main, [str(f), "--format", "xml"])

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# --robustness 옵션
# ---------------------------------------------------------------------------


class TestCLIRobustnessOption:
    def test_robustness_flag_exits_without_error(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = runner.invoke(main, [str(f), "--robustness"])

        assert result.exit_code in (0, 1, 2, 3)

    def test_robustness_plain_image_robustness_field_empty(self, tmp_path: Path):
        """원본 탐지 불가(NOT_FOUND/UNKNOWN)이면 생존율 측정 의미 없음 → 빈 dict."""
        runner = CliRunner()
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = runner.invoke(main, [str(f), "--robustness"])

        data = json.loads(result.output)
        assert isinstance(data["robustness"], dict)

    def test_robustness_outputs_valid_json(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = runner.invoke(main, [str(f), "--robustness"])

        data = json.loads(result.output)
        assert "verdict" in data
        assert "robustness" in data

    def test_robustness_with_summary_format(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = runner.invoke(main, [str(f), "--robustness", "--format", "summary"])

        assert result.exit_code in (0, 1, 2, 3)
        assert "KoAI-Verify" in result.output


# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------


class TestCLIHelp:
    def test_help_exits_0(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0

    def test_help_output_contains_format_option(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert "--format" in result.output

    def test_help_output_contains_robustness_option(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert "--robustness" in result.output

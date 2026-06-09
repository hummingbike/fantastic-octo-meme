"""W12 — 웹 플레이그라운드 단위 테스트.

테스트 대상: playground/app.py

전략:
  - process_image() 함수를 직접 호출 (Gradio 설치 불필요)
  - 합성 JPEG 픽스처로 실 파이프라인 실행 (mock 금지)
  - 에러 처리 및 반환값 형식 검증
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import piexif
from PIL import Image

from playground.app import process_image

# ---------------------------------------------------------------------------
# 헬퍼: 합성 JPEG 생성
# ---------------------------------------------------------------------------


def _plain_jpeg() -> bytes:
    img = Image.new("RGB", (32, 32), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _ai_exif_jpeg() -> bytes:
    img = Image.new("RGB", (32, 32), color=(200, 100, 150))
    exif = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
    exif["Exif"][piexif.ExifIFD.UserComment] = b"ASCII\x00\x00\x00AI Generated"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=piexif.dump(exif))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# process_image() — None / 경로 없음 입력
# ---------------------------------------------------------------------------


class TestProcessImageNoneInput:
    def test_none_returns_error_json(self):
        json_out, summary = process_image(None)

        assert "error" in json_out.lower()

    def test_none_returns_error_summary(self):
        _, summary = process_image(None)

        assert len(summary) > 0

    def test_nonexistent_path_returns_error_json(self, tmp_path: Path):
        json_out, summary = process_image(str(tmp_path / "no_such.jpg"))

        assert "error" in json_out.lower()

    def test_returns_tuple_of_two_strings_on_none(self):
        result = process_image(None)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert all(isinstance(s, str) for s in result)


# ---------------------------------------------------------------------------
# process_image() — 유효한 이미지
# ---------------------------------------------------------------------------


class TestProcessImageValidInput:
    def test_plain_image_returns_tuple(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        result = process_image(str(f))

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_plain_image_json_is_valid(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        json_out, _ = process_image(str(f))

        data = json.loads(json_out)
        assert "verdict" in data

    def test_plain_image_json_has_required_fields(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        json_out, _ = process_image(str(f))

        data = json.loads(json_out)
        for key in ("image", "verdict", "detections", "recommendation", "timestamp"):
            assert key in data, f"JSON 필드 누락: {key}"

    def test_plain_image_summary_contains_koai_header(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        _, summary = process_image(str(f))

        assert "KoAI-Verify" in summary

    def test_plain_image_verdict_non_compliant(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        json_out, _ = process_image(str(f))

        data = json.loads(json_out)
        assert data["verdict"] == "NON_COMPLIANT"

    def test_ai_exif_image_verdict_in_valid_set(self, tmp_path: Path):
        f = tmp_path / "ai.jpg"
        f.write_bytes(_ai_exif_jpeg())

        json_out, _ = process_image(str(f))

        data = json.loads(json_out)
        assert data["verdict"] in ("COMPLIANT", "WARNING", "NON_COMPLIANT")

    def test_summary_contains_verdict_text(self, tmp_path: Path):
        f = tmp_path / "plain.jpg"
        f.write_bytes(_plain_jpeg())

        _, summary = process_image(str(f))

        assert any(kw in summary for kw in ("불충족", "충족", "경고", "판정불가"))


# ---------------------------------------------------------------------------
# process_image() — 잘못된 이미지
# ---------------------------------------------------------------------------


class TestProcessImageInvalidInput:
    def test_corrupt_image_returns_error(self, tmp_path: Path):
        f = tmp_path / "corrupt.jpg"
        f.write_bytes(b"\xff\xd8not a real jpeg!!!")

        json_out, summary = process_image(str(f))

        assert "error" in json_out.lower() or "오류" in summary

    def test_corrupt_image_does_not_raise(self, tmp_path: Path):
        f = tmp_path / "corrupt.jpg"
        f.write_bytes(b"\xff\xd8not a real jpeg!!!")

        result = process_image(str(f))

        assert isinstance(result, tuple)


# ---------------------------------------------------------------------------
# 모듈 구조 검증 (Gradio 없이도 임포트 가능)
# ---------------------------------------------------------------------------


class TestPlaygroundModuleStructure:
    def test_process_image_is_callable(self):
        assert callable(process_image)

    def test_process_image_signature_accepts_none(self):
        result = process_image(None)

        assert isinstance(result, tuple)

    def test_demo_attribute_exists_on_module(self):
        import playground.app as app

        assert hasattr(app, "demo")

"""W6 — C2PADetector 단위 테스트.

테스트 대상: koai_verify/detectors/c2pa_detector.py

픽스처:
  - plain.jpg     : C2PA 없는 JPEG → NOT_FOUND
  - c2pa_test_C.jpg : c2pa-python 공식 테스트 픽스처 (서명 있음) → FOUND
  - invalid bytes  : 지원 불가 포맷 → UNKNOWN
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from koai_verify.detectors.c2pa_detector import (
    C2PADetector,
    _detect_mime,
    _extract_manifest_details,
)
from koai_verify.detectors.result import DetectionResult

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
C2PA_FIXTURE = FIXTURES_DIR / "c2pa" / "c2pa_test_C.jpg"


def _plain_jpeg_bytes() -> bytes:
    """C2PA 매니페스트가 없는 최소 JPEG."""
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color=(200, 200, 200)).save(buf, format="JPEG")
    return buf.getvalue()


def _plain_png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32)).save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 탐지기 이름 및 인터페이스
# ---------------------------------------------------------------------------

class TestC2PADetectorInterface:
    def test_name_is_c2pa(self):
        assert C2PADetector().name == "c2pa"

    def test_is_detector_base_subclass(self):
        from koai_verify.detectors.base import DetectorBase
        assert isinstance(C2PADetector(), DetectorBase)

    def test_detect_returns_detector_output(self):
        from koai_verify.detectors.result import DetectorOutput
        output = C2PADetector().detect(_plain_jpeg_bytes())
        assert isinstance(output, DetectorOutput)

    def test_detect_output_detector_name_is_c2pa(self):
        output = C2PADetector().detect(_plain_jpeg_bytes())
        assert output.detector_name == "c2pa"


# ---------------------------------------------------------------------------
# NOT_FOUND — C2PA 매니페스트 없음
# ---------------------------------------------------------------------------

class TestC2PADetectorNotFound:
    def test_plain_jpeg_returns_not_found(self):
        output = C2PADetector().detect(_plain_jpeg_bytes())
        assert output.result == DetectionResult.NOT_FOUND

    def test_plain_png_returns_not_found(self):
        output = C2PADetector().detect(_plain_png_bytes())
        assert output.result == DetectionResult.NOT_FOUND

    def test_not_found_is_not_found_flag(self):
        output = C2PADetector().detect(_plain_jpeg_bytes())
        assert not output.is_found()

    def test_not_found_is_not_unknown(self):
        output = C2PADetector().detect(_plain_jpeg_bytes())
        assert not output.is_unknown()


# ---------------------------------------------------------------------------
# FOUND — C2PA 매니페스트 있음 (공식 테스트 픽스처)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not C2PA_FIXTURE.exists(),
    reason="C2PA test fixture not found — run: download c2pa test fixtures"
)
class TestC2PADetectorFound:
    def _signed_bytes(self) -> bytes:
        return C2PA_FIXTURE.read_bytes()

    def test_found_result(self):
        output = C2PADetector().detect(self._signed_bytes())
        assert output.result == DetectionResult.FOUND

    def test_found_is_found_flag(self):
        output = C2PADetector().detect(self._signed_bytes())
        assert output.is_found()

    def test_found_manifest_count_positive(self):
        output = C2PADetector().detect(self._signed_bytes())
        assert output.details.get("manifest_count", 0) >= 1

    def test_found_claim_generator_present(self):
        output = C2PADetector().detect(self._signed_bytes())
        cg = output.details.get("claim_generator")
        assert cg is not None and len(cg) > 0

    def test_found_assertion_labels_list(self):
        output = C2PADetector().detect(self._signed_bytes())
        labels = output.details.get("assertion_labels", [])
        assert isinstance(labels, list)

    def test_found_assertion_count_positive(self):
        output = C2PADetector().detect(self._signed_bytes())
        assert output.details.get("assertion_count", 0) >= 1

    def test_found_active_manifest_string(self):
        output = C2PADetector().detect(self._signed_bytes())
        am = output.details.get("active_manifest")
        assert isinstance(am, str) and len(am) > 0


# ---------------------------------------------------------------------------
# UNKNOWN — 지원 불가 포맷
# ---------------------------------------------------------------------------

class TestC2PADetectorUnknown:
    def test_random_bytes_returns_unknown(self):
        output = C2PADetector().detect(b"\x00\x01\x02\x03garbage_data_not_an_image")
        assert output.result == DetectionResult.UNKNOWN

    def test_unknown_reason_in_details(self):
        output = C2PADetector().detect(b"not-an-image")
        assert "reason" in output.details

    def test_unknown_is_unknown_flag(self):
        output = C2PADetector().detect(b"invalid_bytes")
        assert output.is_unknown()

    def test_empty_bytes_returns_unknown(self):
        output = C2PADetector().detect(b"")
        assert output.result == DetectionResult.UNKNOWN


# ---------------------------------------------------------------------------
# detect_safe — 예외 안전 래퍼
# ---------------------------------------------------------------------------

class TestC2PADetectorSafe:
    def test_detect_safe_does_not_raise(self):
        # 최악의 입력에도 예외 없이 반환해야 한다
        output = C2PADetector().detect_safe(b"\xff" * 100)
        assert output is not None

    def test_detect_safe_plain_jpeg_not_found(self):
        output = C2PADetector().detect_safe(_plain_jpeg_bytes())
        assert output.result == DetectionResult.NOT_FOUND


# ---------------------------------------------------------------------------
# 헬퍼 함수
# ---------------------------------------------------------------------------

class TestDetectMimeHelper:
    def test_jpeg_mime(self):
        assert _detect_mime(_plain_jpeg_bytes()) == "image/jpeg"

    def test_png_mime(self):
        assert _detect_mime(_plain_png_bytes()) == "image/png"

    def test_invalid_returns_none(self):
        assert _detect_mime(b"garbage") is None

    def test_empty_returns_none(self):
        assert _detect_mime(b"") is None


class TestExtractManifestDetailsHelper:
    def test_empty_manifest_returns_zero_count(self):
        result = _extract_manifest_details({"manifests": {}})
        assert result["manifest_count"] == 0

    def test_active_manifest_key_present(self):
        result = _extract_manifest_details({
            "active_manifest": "id_1",
            "manifests": {
                "id_1": {
                    "claim_generator": "Tool/1.0",
                    "assertions": [{"label": "c2pa.training-mining"}],
                }
            },
        })
        assert result["active_manifest"] == "id_1"
        assert result["claim_generator"] == "Tool/1.0"
        assert "c2pa.training-mining" in result["assertion_labels"]

    def test_no_active_manifest_key(self):
        result = _extract_manifest_details({"manifests": {}})
        assert result.get("active_manifest") is None

    def test_assertion_count_matches(self):
        result = _extract_manifest_details({
            "active_manifest": "id_1",
            "manifests": {
                "id_1": {
                    "assertions": [
                        {"label": "c2pa.actions.v2"},
                        {"label": "stds.schema-org.CreativeWork"},
                    ]
                }
            },
        })
        assert result["assertion_count"] == 2
        assert len(result["assertion_labels"]) == 2

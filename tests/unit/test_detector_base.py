"""W5 Task1 — koai_verify/detectors/ 단위 테스트.

DetectionResult, DetectorOutput, DetectorBase 검증.
"""
from __future__ import annotations

import pytest

from koai_verify.detectors import DetectionResult, DetectorBase, DetectorOutput

# ---------------------------------------------------------------------------
# DetectionResult 열거형
# ---------------------------------------------------------------------------

class TestDetectionResult:
    def test_three_values_exist(self):
        assert len(DetectionResult) == 3

    def test_found_value(self):
        assert DetectionResult.FOUND == "FOUND"

    def test_not_found_value(self):
        assert DetectionResult.NOT_FOUND == "NOT_FOUND"

    def test_unknown_value(self):
        assert DetectionResult.UNKNOWN == "UNKNOWN"

    def test_is_str_subclass(self):
        assert isinstance(DetectionResult.FOUND, str)

    def test_json_serializable(self):
        import json
        payload = {"result": DetectionResult.FOUND}
        dumped = json.dumps(payload)
        assert '"FOUND"' in dumped


# ---------------------------------------------------------------------------
# DetectorOutput
# ---------------------------------------------------------------------------

class TestDetectorOutput:
    def _make(self, result: DetectionResult) -> DetectorOutput:
        return DetectorOutput(result=result, detector_name="test")

    def test_is_found_true(self):
        assert self._make(DetectionResult.FOUND).is_found()

    def test_is_found_false_for_not_found(self):
        assert not self._make(DetectionResult.NOT_FOUND).is_found()

    def test_is_unknown_true(self):
        assert self._make(DetectionResult.UNKNOWN).is_unknown()

    def test_is_unknown_false_for_found(self):
        assert not self._make(DetectionResult.FOUND).is_unknown()

    def test_details_default_empty(self):
        output = DetectorOutput(result=DetectionResult.FOUND, detector_name="x")
        assert output.details == {}

    def test_confidence_default_none(self):
        output = DetectorOutput(result=DetectionResult.FOUND, detector_name="x")
        assert output.confidence is None

    def test_confidence_valid(self):
        output = DetectorOutput(
            result=DetectionResult.FOUND,
            detector_name="x",
            confidence=0.95,
        )
        assert output.confidence == 0.95

    def test_details_stored(self):
        output = DetectorOutput(
            result=DetectionResult.FOUND,
            detector_name="c2pa",
            details={"manifest_count": 1},
        )
        assert output.details["manifest_count"] == 1


# ---------------------------------------------------------------------------
# DetectorBase 추상 클래스
# ---------------------------------------------------------------------------

class TestDetectorBase:
    def _make_concrete(self, result: DetectionResult, name: str = "stub") -> DetectorBase:
        class StubDetector(DetectorBase):
            @property
            def name(self) -> str:
                return name

            def detect(self, image_bytes: bytes) -> DetectorOutput:
                return DetectorOutput(result=result, detector_name=self.name)

        return StubDetector()

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            DetectorBase()  # type: ignore[abstract]

    def test_concrete_subclass_instantiates(self):
        detector = self._make_concrete(DetectionResult.FOUND)
        assert detector is not None

    def test_detect_returns_output(self):
        detector = self._make_concrete(DetectionResult.FOUND)
        output = detector.detect(b"fake_image")
        assert isinstance(output, DetectorOutput)

    def test_detect_result_propagated(self):
        detector = self._make_concrete(DetectionResult.NOT_FOUND)
        output = detector.detect(b"fake_image")
        assert output.result == DetectionResult.NOT_FOUND

    def test_name_property(self):
        detector = self._make_concrete(DetectionResult.FOUND, name="c2pa_v1")
        assert detector.name == "c2pa_v1"

    def test_detect_safe_returns_unknown_on_exception(self):
        class ErrorDetector(DetectorBase):
            @property
            def name(self) -> str:
                return "error_detector"

            def detect(self, image_bytes: bytes) -> DetectorOutput:
                raise RuntimeError("simulated failure")

        detector = ErrorDetector()
        output = detector.detect_safe(b"data")
        assert output.result == DetectionResult.UNKNOWN
        assert "error" in output.details

    def test_detect_safe_passes_through_on_success(self):
        detector = self._make_concrete(DetectionResult.FOUND)
        output = detector.detect_safe(b"data")
        assert output.result == DetectionResult.FOUND

    def test_missing_name_raises_type_error(self):
        class NoName(DetectorBase):
            def detect(self, image_bytes: bytes) -> DetectorOutput:
                return DetectorOutput(result=DetectionResult.UNKNOWN, detector_name="x")

        with pytest.raises(TypeError):
            NoName()  # type: ignore[abstract]

    def test_missing_detect_raises_type_error(self):
        class NoDetect(DetectorBase):
            @property
            def name(self) -> str:
                return "no_detect"

        with pytest.raises(TypeError):
            NoDetect()  # type: ignore[abstract]

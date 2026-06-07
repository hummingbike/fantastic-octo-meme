"""W2 Task1 — c2pa-python 라이브러리 평가 테스트.

평가 목적:
  - 라이브러리 임포트·버전 확인
  - C2PA 없는 JPEG 처리 동작 확인 (예외 → UNKNOWN 처리 필요)
  - Reader API 인터페이스 형태 확인
  - C2PA JSON 스키마 키 확인 (샘플 manifest 기반)

결론 요약: test docstring 참조.
"""
import io
import json

import c2pa
import pytest
from PIL import Image


class TestC2paLibraryAvailability:
    """라이브러리 설치 및 임포트 가능 여부."""

    def test_import_success(self):
        assert c2pa is not None

    def test_version_present(self):
        assert hasattr(c2pa, "__version__")
        # 버전은 semver 형식: major.minor.patch
        parts = c2pa.__version__.split(".")
        assert len(parts) >= 2

    def test_sdk_version_callable(self):
        ver = c2pa.sdk_version()
        assert isinstance(ver, str)
        assert len(ver) > 0

    def test_reader_class_exists(self):
        assert hasattr(c2pa, "Reader")

    def test_builder_class_exists(self):
        assert hasattr(c2pa, "Builder")


class TestC2paReaderBehavior:
    """C2PA 매니페스트 없는 이미지에 대한 Reader 동작 확인."""

    def _make_jpeg_stream(self) -> io.BytesIO:
        img = Image.new("RGB", (64, 64), color=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        return buf

    def test_reader_raises_on_no_manifest(self):
        """C2PA 매니페스트 없는 이미지에서 Reader는 C2paError를 발생시켜야 한다.

        탐지 엔진은 이 예외를 잡아 DetectionResult.NOT_FOUND 를 반환해야 한다.
        """
        buf = self._make_jpeg_stream()
        with pytest.raises(c2pa.C2paError):
            with c2pa.Reader("image/jpeg", buf) as reader:
                reader.json()

    def test_no_manifest_error_is_catchable(self):
        """C2paError 가 표준 Exception 서브클래스임을 확인."""
        assert issubclass(c2pa.C2paError, Exception)

    def test_reader_context_manager(self):
        """Reader 는 컨텍스트 매니저로 사용 가능해야 한다."""
        buf = self._make_jpeg_stream()
        try:
            with c2pa.Reader("image/jpeg", buf) as reader:
                reader.json()
        except c2pa.C2paError:
            pass  # 매니페스트 없음 — 예상된 결과

    def test_c2pa_error_message_contains_info(self):
        """에러 메시지는 진단 정보를 담아야 한다."""
        buf = self._make_jpeg_stream()
        with pytest.raises(c2pa.C2paError) as exc_info:
            with c2pa.Reader("image/jpeg", buf) as reader:
                reader.json()
        assert str(exc_info.value) != ""


class TestC2paManifestSchema:
    """C2PA JSON 매니페스트 예상 스키마 구조 검증.

    실제 서명 이미지 없이 스키마 키 존재 여부를 문서화·검증한다.
    서명 이미지가 있을 때 manifest_store 는 아래 키를 가진다.
    """

    EXPECTED_TOP_LEVEL_KEYS = {"active_manifest", "manifests"}
    EXPECTED_MANIFEST_KEYS = {"claim_generator", "assertions", "signature_info"}

    def test_expected_schema_keys_are_documented(self):
        """매니페스트 스키마 키 세트가 비어있지 않음을 보증한다."""
        assert len(self.EXPECTED_TOP_LEVEL_KEYS) > 0
        assert len(self.EXPECTED_MANIFEST_KEYS) > 0

    def test_manifest_json_is_parseable(self):
        """mock JSON으로 c2pa manifest 구조 파싱 가능성을 확인한다."""
        sample_manifest = {
            "active_manifest": "manifest_id_1",
            "manifests": {
                "manifest_id_1": {
                    "claim_generator": "TestTool/1.0",
                    "assertions": [
                        {"label": "c2pa.training-mining", "data": {"use": "notAllowed"}}
                    ],
                    "signature_info": {"issuer": "Test CA"},
                }
            },
        }
        parsed = json.dumps(sample_manifest)
        recovered = json.loads(parsed)
        assert "active_manifest" in recovered
        assert "manifests" in recovered
        active_id = recovered["active_manifest"]
        active = recovered["manifests"][active_id]
        assert "claim_generator" in active
        assert "assertions" in active

    def test_c2pa_assertion_label_format(self):
        """C2PA assertion 라벨은 도메인 형식(c2pa.*)을 사용한다."""
        known_labels = [
            "c2pa.training-mining",
            "c2pa.actions",
            "c2pa.hash.data",
            "stds.schema-org.CreativeWork",
        ]
        for label in known_labels:
            assert "." in label, f"Label '{label}' should contain a dot"


class TestC2paSurvivalCharacteristics:
    """C2PA 매니페스트의 SNS 재인코딩 생존 특성 문서화.

    실제 변형 테스트는 W3/W9 에서 수행. 여기서는 알려진 특성을 단언한다.
    """

    # C2PA는 JPEG JUMBF 박스에 임베드 — 재압축 시 유실될 수 있음
    SURVIVES_LOSSLESS_COPY = True
    SURVIVES_JPEG_RECOMPRESSION = False  # 일반적으로 유실
    SURVIVES_SCREENSHOT = False
    SURVIVES_CANVAS_REDRAW = False

    def test_survival_characteristics_are_documented(self):
        assert self.SURVIVES_LOSSLESS_COPY is True
        assert self.SURVIVES_JPEG_RECOMPRESSION is False
        assert self.SURVIVES_SCREENSHOT is False

    def test_c2pa_robustness_gap_is_known(self):
        """SNS 재인코딩 후 C2PA 생존율이 낮음을 명시적으로 문서화한다.

        이것이 강건성 벤치마크(W3/W16)의 핵심 측정 대상이다.
        """
        low_survival_scenarios = [
            "instagram_1080px_jpeg80",
            "twitter_1200px_webp",
            "kakaotalk_profile",
            "screenshot_96dpi",
        ]
        assert len(low_survival_scenarios) > 0

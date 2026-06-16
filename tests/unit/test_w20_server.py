"""W20 — 호스팅 검증 API v0 단위 테스트.

FastAPI TestClient + httpx 기반.
실제 이미지 픽스처를 사용해 검증 파이프라인을 end-to-end 검증한다.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest

_ROOT = Path(__file__).parent.parent.parent
_SAMPLE_JPEG = _ROOT / "tests" / "fixtures" / "samples" / "firefly" / "firefly_01.jpg"
_SERVER_PKG = _ROOT / "koai_verify" / "server"


# ─────────────────────────────────────────────────────────────────────────────
# 패키지 구조
# ─────────────────────────────────────────────────────────────────────────────


class TestServerPackageStructure:
    """서버 패키지 파일 존재 여부."""

    def test_server_package_exists(self):
        assert _SERVER_PKG.exists()

    def test_app_module_exists(self):
        assert (_SERVER_PKG / "app.py").exists()

    def test_auth_module_exists(self):
        assert (_SERVER_PKG / "auth.py").exists()

    def test_usage_module_exists(self):
        assert (_SERVER_PKG / "usage.py").exists()

    def test_init_exists(self):
        assert (_SERVER_PKG / "__init__.py").exists()


# ─────────────────────────────────────────────────────────────────────────────
# 사용량 추적기 (usage.py)
# ─────────────────────────────────────────────────────────────────────────────


class TestUsageTracker:
    """UsageTracker 단위 테스트."""

    def _make_tracker(self):
        from koai_verify.server.usage import UsageTracker

        return UsageTracker()

    def test_initial_stats_empty(self):
        tracker = self._make_tracker()
        stats = tracker.get_stats()
        assert stats.total_requests == 0
        assert stats.total_image_bytes == 0
        assert stats.verdict_counts == {}

    def test_record_increments_total_requests(self):
        tracker = self._make_tracker()
        tracker.record(image_size_bytes=1024, verdict="COMPLIANT", api_key="testkey", duration_ms=10.0)
        assert tracker.get_stats().total_requests == 1

    def test_record_accumulates_bytes(self):
        tracker = self._make_tracker()
        tracker.record(image_size_bytes=500, verdict="COMPLIANT", api_key="k", duration_ms=5.0)
        tracker.record(image_size_bytes=300, verdict="NON_COMPLIANT", api_key="k", duration_ms=5.0)
        assert tracker.get_stats().total_image_bytes == 800

    def test_record_counts_verdict(self):
        tracker = self._make_tracker()
        tracker.record(image_size_bytes=100, verdict="COMPLIANT", api_key="k", duration_ms=1.0)
        tracker.record(image_size_bytes=100, verdict="COMPLIANT", api_key="k", duration_ms=1.0)
        tracker.record(image_size_bytes=100, verdict="WARNING", api_key="k", duration_ms=1.0)
        counts = tracker.get_stats().verdict_counts
        assert counts["COMPLIANT"] == 2
        assert counts["WARNING"] == 1

    def test_api_key_prefix_truncated(self):
        tracker = self._make_tracker()
        tracker.record(image_size_bytes=100, verdict="UNKNOWN", api_key="abcdefghijklmnop", duration_ms=1.0)
        rec = tracker.get_stats().records[0]
        assert rec.api_key_prefix == "abcdefgh..."
        assert "ijklmnop" not in rec.api_key_prefix

    def test_short_key_stored_as_is(self):
        tracker = self._make_tracker()
        tracker.record(image_size_bytes=100, verdict="UNKNOWN", api_key="short", duration_ms=1.0)
        rec = tracker.get_stats().records[0]
        assert rec.api_key_prefix == "short"

    def test_to_dict_structure(self):
        tracker = self._make_tracker()
        tracker.record(image_size_bytes=200, verdict="COMPLIANT", api_key="k", duration_ms=2.0)
        d = tracker.get_stats().to_dict()
        assert "total_requests" in d
        assert "total_image_bytes" in d
        assert "verdict_counts" in d
        assert "records" in d

    def test_record_has_timestamp(self):
        tracker = self._make_tracker()
        tracker.record(image_size_bytes=100, verdict="COMPLIANT", api_key="k", duration_ms=1.0)
        rec = tracker.get_stats().records[0]
        assert rec.timestamp.endswith("Z")

    def test_multiple_records_preserved(self):
        tracker = self._make_tracker()
        for i in range(5):
            tracker.record(image_size_bytes=i * 100, verdict="UNKNOWN", api_key="k", duration_ms=float(i))
        assert len(tracker.get_stats().records) == 5

    def test_get_stats_returns_copy(self):
        tracker = self._make_tracker()
        s1 = tracker.get_stats()
        tracker.record(image_size_bytes=100, verdict="COMPLIANT", api_key="k", duration_ms=1.0)
        s2 = tracker.get_stats()
        assert s1.total_requests == 0
        assert s2.total_requests == 1

    def test_persist_writes_file(self, tmp_path):
        from koai_verify.server.usage import UsageTracker

        path = tmp_path / "usage.json"
        tracker = UsageTracker(persist_path=path)
        tracker.record(image_size_bytes=100, verdict="COMPLIANT", api_key="k", duration_ms=1.0)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["total_requests"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 인증 모듈 (auth.py)
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthModule:
    """auth.py 단위 테스트."""

    def test_dev_mode_true(self):
        from koai_verify.server.auth import is_dev_mode

        with patch.dict(os.environ, {"KOAI_DEV_MODE": "true"}):
            assert is_dev_mode() is True

    def test_dev_mode_false_by_default(self):
        from koai_verify.server.auth import is_dev_mode

        env = {k: v for k, v in os.environ.items() if k != "KOAI_DEV_MODE"}
        with patch.dict(os.environ, env, clear=True):
            assert is_dev_mode() is False

    def test_dev_mode_case_insensitive(self):
        from koai_verify.server.auth import is_dev_mode

        with patch.dict(os.environ, {"KOAI_DEV_MODE": "TRUE"}):
            assert is_dev_mode() is True

    def test_env_keys_parsed(self):
        from koai_verify.server.auth import get_valid_keys

        with patch.dict(os.environ, {"KOAI_API_KEYS": "key1,key2,key3"}):
            keys = get_valid_keys()
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys

    def test_env_keys_strips_whitespace(self):
        from koai_verify.server.auth import get_valid_keys

        with patch.dict(os.environ, {"KOAI_API_KEYS": " key1 , key2 "}):
            keys = get_valid_keys()
        assert "key1" in keys
        assert "key2" in keys

    def test_config_file_keys(self, tmp_path):
        from koai_verify.server import auth

        config = tmp_path / "api_keys.json"
        config.write_text(json.dumps(["filekey1", "filekey2"]))

        original = auth._CONFIG_PATH
        auth._CONFIG_PATH = config
        try:
            keys = auth._load_config_keys()
        finally:
            auth._CONFIG_PATH = original

        assert "filekey1" in keys
        assert "filekey2" in keys

    def test_config_file_missing_returns_empty(self, tmp_path):
        from koai_verify.server import auth

        original = auth._CONFIG_PATH
        auth._CONFIG_PATH = tmp_path / "nonexistent.json"
        try:
            keys = auth._load_config_keys()
        finally:
            auth._CONFIG_PATH = original

        assert keys == set()

    def test_config_file_invalid_json_returns_empty(self, tmp_path):
        from koai_verify.server import auth

        config = tmp_path / "api_keys.json"
        config.write_text("not-json")
        original = auth._CONFIG_PATH
        auth._CONFIG_PATH = config
        try:
            keys = auth._load_config_keys()
        finally:
            auth._CONFIG_PATH = original

        assert keys == set()


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI 앱 (app.py) — TestClient
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def dev_mode_env() -> Generator[None, None, None]:
    """KOAI_DEV_MODE=true 로 인증 우회."""
    with patch.dict(os.environ, {"KOAI_DEV_MODE": "true", "KOAI_API_KEYS": ""}):
        yield


@pytest.fixture()
def api_key_env() -> Generator[None, None, None]:
    """KOAI_API_KEYS=testkey123 으로 키 인증 활성화."""
    env = {k: v for k, v in os.environ.items() if k != "KOAI_DEV_MODE"}
    env["KOAI_API_KEYS"] = "testkey123"
    env["KOAI_DEV_MODE"] = "false"
    with patch.dict(os.environ, env, clear=True):
        yield


@pytest.fixture()
def client(dev_mode_env):
    """개발 모드 TestClient (인증 없음)."""
    from fastapi.testclient import TestClient

    from koai_verify.server.app import app
    from koai_verify.server.usage import UsageTracker, set_tracker

    tracker = UsageTracker()
    set_tracker(tracker)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_client(api_key_env):
    """키 인증 모드 TestClient."""
    from fastapi.testclient import TestClient

    from koai_verify.server.app import app
    from koai_verify.server.usage import UsageTracker, set_tracker

    tracker = UsageTracker()
    set_tracker(tracker)
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    """/v0/health 엔드포인트 테스트."""

    def test_health_returns_200(self, client):
        resp = client.get("/v0/health")
        assert resp.status_code == 200

    def test_health_body_ok(self, client):
        resp = client.get("/v0/health")
        assert resp.json()["status"] == "ok"

    def test_health_has_version(self, client):
        resp = client.get("/v0/health")
        assert "version" in resp.json()

    def test_health_no_auth_required(self):
        """헬스 체크는 인증 없이도 접근 가능해야 한다."""
        with patch.dict(os.environ, {"KOAI_DEV_MODE": "false", "KOAI_API_KEYS": "somekey"}):
            from fastapi.testclient import TestClient

            from koai_verify.server.app import app

            with TestClient(app) as c:
                resp = c.get("/v0/health")
        assert resp.status_code == 200


class TestVerifyEndpoint:
    """/v0/verify 엔드포인트 테스트."""

    def _read_sample(self) -> bytes:
        return _SAMPLE_JPEG.read_bytes()

    def test_verify_returns_200_with_valid_image(self, client):
        data = self._read_sample()
        resp = client.post("/v0/verify", files={"file": ("test.jpg", data, "image/jpeg")})
        assert resp.status_code == 200

    def test_verify_response_has_verdict(self, client):
        data = self._read_sample()
        resp = client.post("/v0/verify", files={"file": ("test.jpg", data, "image/jpeg")})
        body = resp.json()
        assert "verdict" in body
        assert body["verdict"] in ("COMPLIANT", "NON_COMPLIANT", "WARNING", "UNKNOWN")

    def test_verify_response_has_detections(self, client):
        data = self._read_sample()
        resp = client.post("/v0/verify", files={"file": ("test.jpg", data, "image/jpeg")})
        body = resp.json()
        assert "detections" in body
        assert isinstance(body["detections"], dict)

    def test_verify_response_has_recommendation(self, client):
        data = self._read_sample()
        resp = client.post("/v0/verify", files={"file": ("test.jpg", data, "image/jpeg")})
        body = resp.json()
        assert "recommendation" in body

    def test_verify_response_has_timestamp(self, client):
        data = self._read_sample()
        resp = client.post("/v0/verify", files={"file": ("test.jpg", data, "image/jpeg")})
        body = resp.json()
        assert "timestamp" in body

    def test_verify_response_has_triggered_rules(self, client):
        data = self._read_sample()
        resp = client.post("/v0/verify", files={"file": ("test.jpg", data, "image/jpeg")})
        body = resp.json()
        assert "triggered_rules" in body
        assert isinstance(body["triggered_rules"], list)

    def test_verify_response_has_image_hash(self, client):
        data = self._read_sample()
        resp = client.post("/v0/verify", files={"file": ("test.jpg", data, "image/jpeg")})
        body = resp.json()
        assert "image" in body
        assert body["image"].startswith("sha256:")

    def test_verify_empty_file_returns_422(self, client):
        resp = client.post("/v0/verify", files={"file": ("empty.jpg", b"", "image/jpeg")})
        assert resp.status_code == 422

    def test_verify_invalid_bytes_returns_422(self, client):
        resp = client.post("/v0/verify", files={"file": ("bad.jpg", b"notanimage", "image/jpeg")})
        assert resp.status_code == 422

    def test_verify_png_accepted(self, client):
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (10, 10), color=(128, 128, 128)).save(buf, format="PNG")
        buf.seek(0)
        resp = client.post("/v0/verify", files={"file": ("test.png", buf.read(), "image/png")})
        assert resp.status_code == 200

    def test_verify_webp_accepted(self, client):
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (10, 10), color=(64, 64, 64)).save(buf, format="WEBP")
        buf.seek(0)
        resp = client.post("/v0/verify", files={"file": ("test.webp", buf.read(), "image/webp")})
        assert resp.status_code == 200

    def test_verify_robustness_false_by_default(self, client):
        data = self._read_sample()
        resp = client.post("/v0/verify", files={"file": ("test.jpg", data, "image/jpeg")})
        body = resp.json()
        assert body.get("robustness", {}) == {}

    def test_verify_records_usage(self, client, dev_mode_env):
        from koai_verify.server.usage import get_tracker

        data = self._read_sample()
        client.post("/v0/verify", files={"file": ("test.jpg", data, "image/jpeg")})
        stats = get_tracker().get_stats()
        assert stats.total_requests >= 1

    def test_verify_usage_records_image_size(self, client):
        from koai_verify.server.usage import get_tracker

        data = self._read_sample()
        client.post("/v0/verify", files={"file": ("test.jpg", data, "image/jpeg")})
        stats = get_tracker().get_stats()
        assert stats.total_image_bytes > 0


class TestAuthEnforcement:
    """API 키 인증 강제 테스트."""

    def test_no_key_when_keys_set_returns_401(self, auth_client):
        data = _SAMPLE_JPEG.read_bytes()
        resp = auth_client.post("/v0/verify", files={"file": ("test.jpg", data, "image/jpeg")})
        assert resp.status_code == 401

    def test_wrong_key_returns_403(self, auth_client):
        data = _SAMPLE_JPEG.read_bytes()
        resp = auth_client.post(
            "/v0/verify",
            files={"file": ("test.jpg", data, "image/jpeg")},
            headers={"X-API-Key": "wrongkey"},
        )
        assert resp.status_code == 403

    def test_correct_key_returns_200(self, auth_client):
        data = _SAMPLE_JPEG.read_bytes()
        resp = auth_client.post(
            "/v0/verify",
            files={"file": ("test.jpg", data, "image/jpeg")},
            headers={"X-API-Key": "testkey123"},
        )
        assert resp.status_code == 200

    def test_dev_mode_bypasses_auth(self):
        with patch.dict(os.environ, {"KOAI_DEV_MODE": "true", "KOAI_API_KEYS": "secretkey"}):
            from fastapi.testclient import TestClient

            from koai_verify.server.app import app

            with TestClient(app) as c:
                resp = c.get("/v0/health")
        assert resp.status_code == 200

    def test_usage_endpoint_requires_auth(self, auth_client):
        resp = auth_client.get("/v0/usage")
        assert resp.status_code == 401

    def test_usage_endpoint_with_key(self, auth_client):
        resp = auth_client.get("/v0/usage", headers={"X-API-Key": "testkey123"})
        assert resp.status_code == 200


class TestUsageEndpoint:
    """/v0/usage 엔드포인트 테스트."""

    def test_usage_returns_200(self, client):
        resp = client.get("/v0/usage")
        assert resp.status_code == 200

    def test_usage_has_total_requests(self, client):
        resp = client.get("/v0/usage")
        body = resp.json()
        assert "total_requests" in body

    def test_usage_has_verdict_counts(self, client):
        resp = client.get("/v0/usage")
        body = resp.json()
        assert "verdict_counts" in body

    def test_usage_has_total_bytes(self, client):
        resp = client.get("/v0/usage")
        body = resp.json()
        assert "total_image_bytes" in body

    def test_usage_increments_after_verify(self, client):
        data = _SAMPLE_JPEG.read_bytes()
        client.post("/v0/verify", files={"file": ("test.jpg", data, "image/jpeg")})
        resp = client.get("/v0/usage")
        assert resp.json()["total_requests"] >= 1

    def test_usage_verdict_counts_populated(self, client):
        data = _SAMPLE_JPEG.read_bytes()
        client.post("/v0/verify", files={"file": ("test.jpg", data, "image/jpeg")})
        resp = client.get("/v0/usage")
        assert len(resp.json()["verdict_counts"]) >= 1


class TestSafeSuffixHelper:
    """_safe_suffix 내부 헬퍼 테스트."""

    def test_jpg_suffix(self):
        from koai_verify.server.app import _safe_suffix

        assert _safe_suffix("photo.jpg") == ".jpg"

    def test_jpeg_suffix(self):
        from koai_verify.server.app import _safe_suffix

        assert _safe_suffix("photo.jpeg") == ".jpeg"

    def test_png_suffix(self):
        from koai_verify.server.app import _safe_suffix

        assert _safe_suffix("photo.png") == ".png"

    def test_webp_suffix(self):
        from koai_verify.server.app import _safe_suffix

        assert _safe_suffix("photo.webp") == ".webp"

    def test_unknown_suffix_returns_bin(self):
        from koai_verify.server.app import _safe_suffix

        assert _safe_suffix("photo.exe") == ".bin"

    def test_none_returns_bin(self):
        from koai_verify.server.app import _safe_suffix

        assert _safe_suffix(None) == ".bin"

    def test_no_extension_returns_bin(self):
        from koai_verify.server.app import _safe_suffix

        assert _safe_suffix("photonoext") == ".bin"

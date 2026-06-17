"""W22 — 공유 가능한 배지/리포트(바이럴 훅): badge.py, report_store.py, /v0/share·/v0/badge 엔드포인트, 문서 검증."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest

_ROOT = Path(__file__).parent.parent.parent
_BADGE_DOC = _ROOT / "docs" / "badge_sharing.md"
_BADGE_MOD = _ROOT / "koai_verify" / "report" / "badge.py"
_REPORT_STORE_MOD = _ROOT / "koai_verify" / "server" / "report_store.py"
_SAMPLE_JPEG = _ROOT / "tests" / "fixtures" / "samples" / "firefly" / "firefly_01.jpg"


# ─────────────────────────────────────────────────────────────────────────────
# Task 1: koai_verify/report/badge.py — SVG 배지 생성
# ─────────────────────────────────────────────────────────────────────────────


class TestBadgeModuleStructure:
    def test_badge_module_exists(self):
        assert _BADGE_MOD.exists()

    def test_badge_module_nonempty(self):
        assert len(_BADGE_MOD.read_text(encoding="utf-8")) > 300

    def test_module_imports_cleanly(self):
        from koai_verify.report.badge import generate_badge_svg

        assert generate_badge_svg is not None


class TestBadgeColor:
    def test_compliant_is_green(self):
        from koai_verify.report.badge import badge_color

        assert badge_color("COMPLIANT") == "#4c1"

    def test_non_compliant_is_red(self):
        from koai_verify.report.badge import badge_color

        assert badge_color("NON_COMPLIANT") == "#e05d44"

    def test_warning_is_yellow(self):
        from koai_verify.report.badge import badge_color

        assert badge_color("WARNING") == "#dfb317"

    def test_unknown_is_gray(self):
        from koai_verify.report.badge import badge_color

        assert badge_color("UNKNOWN") == "#9f9f9f"

    def test_unrecognized_value_falls_back_to_unknown_color(self):
        from koai_verify.report.badge import badge_color

        assert badge_color("NOT_A_REAL_VERDICT") == badge_color("UNKNOWN")


class TestGenerateBadgeSvg:
    def test_returns_valid_svg_root(self):
        from koai_verify.report.badge import generate_badge_svg

        svg = generate_badge_svg("COMPLIANT")
        assert svg.startswith("<svg")
        assert svg.rstrip().endswith("</svg>")

    def test_contains_verdict_text(self):
        from koai_verify.report.badge import generate_badge_svg

        svg = generate_badge_svg("NON_COMPLIANT")
        assert "NON_COMPLIANT" in svg

    def test_contains_default_label(self):
        from koai_verify.report.badge import generate_badge_svg

        svg = generate_badge_svg("WARNING")
        assert "KoAI-Verify" in svg

    def test_custom_label_used(self):
        from koai_verify.report.badge import generate_badge_svg

        svg = generate_badge_svg("COMPLIANT", label="MyApp")
        assert "MyApp" in svg
        assert "KoAI-Verify" not in svg

    def test_contains_color_for_verdict(self):
        from koai_verify.report.badge import generate_badge_svg

        svg = generate_badge_svg("COMPLIANT")
        assert "#4c1" in svg

    def test_unknown_verdict_does_not_raise(self):
        from koai_verify.report.badge import generate_badge_svg

        svg = generate_badge_svg("TOTALLY_UNRECOGNIZED")
        assert "<svg" in svg
        assert "#9f9f9f" in svg

    def test_longer_verdict_produces_wider_svg(self):
        from koai_verify.report.badge import generate_badge_svg

        narrow = generate_badge_svg("OK")
        wide = generate_badge_svg("NON_COMPLIANT")

        def _width(svg: str) -> int:
            return int(svg.split('width="')[1].split('"')[0])

        assert _width(wide) > _width(narrow)

    def test_is_valid_xml(self):
        import xml.etree.ElementTree as ET

        from koai_verify.report.badge import generate_badge_svg

        svg = generate_badge_svg("COMPLIANT")
        ET.fromstring(svg)  # raises on malformed XML


# ─────────────────────────────────────────────────────────────────────────────
# Task 2: koai_verify/server/report_store.py — 공개 공유 리포트 저장소
# ─────────────────────────────────────────────────────────────────────────────


class TestReportStoreModuleStructure:
    def test_report_store_module_exists(self):
        assert _REPORT_STORE_MOD.exists()

    def test_module_imports_cleanly(self):
        from koai_verify.server.report_store import ReportStore

        assert ReportStore is not None


class TestExtractReportId:
    def test_strips_sha256_prefix(self):
        from koai_verify.server.report_store import extract_report_id

        assert extract_report_id("sha256:abcdef") == "abcdef"

    def test_returns_as_is_without_prefix(self):
        from koai_verify.server.report_store import extract_report_id

        assert extract_report_id("abcdef") == "abcdef"


class TestReportStore:
    def _make_store(self):
        from koai_verify.server.report_store import ReportStore

        return ReportStore()

    def test_save_returns_report_id(self):
        store = self._make_store()
        report_id = store.save({"image": "sha256:deadbeef", "verdict": "COMPLIANT"})
        assert report_id == "deadbeef"

    def test_get_returns_saved_report(self):
        store = self._make_store()
        report_id = store.save({"image": "sha256:deadbeef", "verdict": "COMPLIANT"})
        assert store.get(report_id) == {"image": "sha256:deadbeef", "verdict": "COMPLIANT"}

    def test_get_missing_returns_none(self):
        store = self._make_store()
        assert store.get("nonexistent") is None

    def test_save_overwrites_same_image(self):
        store = self._make_store()
        store.save({"image": "sha256:abc", "verdict": "WARNING"})
        report_id = store.save({"image": "sha256:abc", "verdict": "COMPLIANT"})
        assert store.get(report_id)["verdict"] == "COMPLIANT"

    def test_clear_empties_store(self):
        store = self._make_store()
        report_id = store.save({"image": "sha256:abc", "verdict": "COMPLIANT"})
        store.clear()
        assert store.get(report_id) is None

    def test_get_report_store_returns_singleton(self):
        from koai_verify.server.report_store import get_report_store

        assert get_report_store() is get_report_store()

    def test_set_report_store_replaces_singleton(self):
        from koai_verify.server.report_store import ReportStore, get_report_store, set_report_store

        original = get_report_store()
        replacement = ReportStore()
        set_report_store(replacement)
        try:
            assert get_report_store() is replacement
        finally:
            set_report_store(original)


# ─────────────────────────────────────────────────────────────────────────────
# Task 3: /v0/verify(share=true), /v0/share/{id}, /v0/badge/{id}.svg
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def dev_mode_env() -> Generator[None, None, None]:
    with patch.dict(os.environ, {"KOAI_DEV_MODE": "true", "KOAI_API_KEYS": ""}):
        yield


@pytest.fixture()
def client(dev_mode_env):
    from fastapi.testclient import TestClient

    from koai_verify.server.app import app
    from koai_verify.server.report_store import ReportStore, set_report_store
    from koai_verify.server.usage import UsageTracker, set_tracker

    set_tracker(UsageTracker())
    set_report_store(ReportStore())
    with TestClient(app) as c:
        yield c


class TestVerifyShareOptIn:
    def _read_sample(self) -> bytes:
        return _SAMPLE_JPEG.read_bytes()

    def test_share_false_by_default_no_report_id(self, client):
        data = self._read_sample()
        resp = client.post("/v0/verify", files={"file": ("test.jpg", data, "image/jpeg")})
        assert "report_id" not in resp.json()

    def test_share_true_returns_report_id(self, client):
        data = self._read_sample()
        resp = client.post(
            "/v0/verify",
            files={"file": ("test.jpg", data, "image/jpeg")},
            data={"share": "true"},
        )
        body = resp.json()
        assert "report_id" in body
        assert "share_url" in body
        assert "badge_url" in body

    def test_share_url_points_to_share_endpoint(self, client):
        data = self._read_sample()
        resp = client.post(
            "/v0/verify",
            files={"file": ("test.jpg", data, "image/jpeg")},
            data={"share": "true"},
        )
        body = resp.json()
        assert body["share_url"] == f"/v0/share/{body['report_id']}"

    def test_badge_url_points_to_badge_endpoint(self, client):
        data = self._read_sample()
        resp = client.post(
            "/v0/verify",
            files={"file": ("test.jpg", data, "image/jpeg")},
            data={"share": "true"},
        )
        body = resp.json()
        assert body["badge_url"] == f"/v0/badge/{body['report_id']}.svg"


class TestShareEndpoint:
    def _verify_with_share(self, client) -> dict:
        data = _SAMPLE_JPEG.read_bytes()
        resp = client.post(
            "/v0/verify",
            files={"file": ("test.jpg", data, "image/jpeg")},
            data={"share": "true"},
        )
        return resp.json()

    def test_share_endpoint_returns_200(self, client):
        body = self._verify_with_share(client)
        resp = client.get(body["share_url"])
        assert resp.status_code == 200

    def test_share_endpoint_returns_full_report(self, client):
        body = self._verify_with_share(client)
        resp = client.get(body["share_url"])
        shared = resp.json()
        assert shared["verdict"] == body["verdict"]
        assert shared["image"] == body["image"]

    def test_share_endpoint_no_auth_required(self):
        with patch.dict(os.environ, {"KOAI_DEV_MODE": "false", "KOAI_API_KEYS": "secretkey"}):
            from fastapi.testclient import TestClient

            from koai_verify.server.app import app
            from koai_verify.server.report_store import ReportStore, set_report_store

            store = ReportStore()
            store.save({"image": "sha256:abc123", "verdict": "COMPLIANT"})
            set_report_store(store)

            with TestClient(app) as c:
                resp = c.get("/v0/share/abc123")
        assert resp.status_code == 200

    def test_share_endpoint_404_for_unknown_id(self, client):
        resp = client.get("/v0/share/doesnotexist")
        assert resp.status_code == 404


class TestBadgeEndpoint:
    def _verify_with_share(self, client) -> dict:
        data = _SAMPLE_JPEG.read_bytes()
        resp = client.post(
            "/v0/verify",
            files={"file": ("test.jpg", data, "image/jpeg")},
            data={"share": "true"},
        )
        return resp.json()

    def test_badge_endpoint_returns_200(self, client):
        body = self._verify_with_share(client)
        resp = client.get(body["badge_url"])
        assert resp.status_code == 200

    def test_badge_content_type_is_svg(self, client):
        body = self._verify_with_share(client)
        resp = client.get(body["badge_url"])
        assert resp.headers["content-type"].startswith("image/svg+xml")

    def test_badge_body_contains_verdict(self, client):
        body = self._verify_with_share(client)
        resp = client.get(body["badge_url"])
        assert body["verdict"] in resp.text

    def test_badge_unknown_id_falls_back_to_unknown_200(self, client):
        resp = client.get("/v0/badge/doesnotexist.svg")
        assert resp.status_code == 200
        assert "UNKNOWN" in resp.text

    def test_badge_endpoint_no_auth_required(self):
        with patch.dict(os.environ, {"KOAI_DEV_MODE": "false", "KOAI_API_KEYS": "secretkey"}):
            from fastapi.testclient import TestClient

            from koai_verify.server.app import app

            with TestClient(app) as c:
                resp = c.get("/v0/badge/anything.svg")
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Task 4: docs/badge_sharing.md
# ─────────────────────────────────────────────────────────────────────────────


class TestBadgeSharingDocument:
    @pytest.fixture(scope="class")
    def content(self) -> str:
        return _BADGE_DOC.read_text(encoding="utf-8")

    def test_file_exists(self):
        assert _BADGE_DOC.exists()

    def test_is_nonempty(self, content: str):
        assert len(content) > 1000

    def test_starts_with_heading(self, content: str):
        assert content.startswith("#")

    def test_has_background_section(self, content: str):
        assert "배경" in content

    def test_mentions_shields_io_inspiration(self, content: str):
        assert "shields.io" in content

    def test_documents_share_query_param(self, content: str):
        assert "share=true" in content

    def test_documents_share_endpoint(self, content: str):
        assert "/v0/share/" in content

    def test_documents_badge_endpoint(self, content: str):
        assert "/v0/badge/" in content

    def test_has_markdown_embed_example(self, content: str):
        assert "![KoAI-Verify]" in content

    def test_has_color_table(self, content: str):
        for verdict in ("COMPLIANT", "NON_COMPLIANT", "WARNING", "UNKNOWN"):
            assert verdict in content

    def test_has_design_decisions_section(self, content: str):
        assert "설계 결정" in content

    def test_explains_report_id_uses_hash(self, content: str):
        assert "해시" in content

    def test_has_limitations_section(self, content: str):
        assert "한계" in content

    def test_mentions_in_memory_limitation(self, content: str):
        assert "인메모리" in content

    def test_no_hardcoded_personal_paths(self, content: str):
        assert "/Users/okestro" not in content

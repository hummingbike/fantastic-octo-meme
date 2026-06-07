"""W4 Task1 — 합성 샘플 픽스처 검증.

각 도구 픽스처가:
  - 유효한 JPEG 인지
  - 예상 메타데이터 패턴을 가지는지
  - 디렉터리 구조가 완전한지

픽스처는 tests/fixtures/make_synthetic_samples.py 로 생성된다.
"""
from __future__ import annotations

from pathlib import Path

import piexif
import pytest
from PIL import Image

SAMPLES_DIR = Path(__file__).parent.parent / "fixtures" / "samples"

KNOWN_TOOLS = [
    "stable_diffusion",
    "comfyui",
    "midjourney",
    "dalle3",
    "firefly",
    "drapart",
    "genape",
    "vela",
    "jeditor",
]

KOREAN_TOOLS = ["drapart", "genape", "vela", "jeditor"]
INTERNATIONAL_TOOLS = ["stable_diffusion", "comfyui", "midjourney", "dalle3", "firefly"]


def _jpeg_files(tool: str) -> list[Path]:
    return sorted((SAMPLES_DIR / tool).glob("*.jpg"))


def _exif(path: Path) -> dict:
    try:
        return piexif.load(str(path))
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# 디렉터리 구조 검증
# ---------------------------------------------------------------------------

class TestSamplesDirectoryStructure:
    def test_samples_dir_exists(self):
        assert SAMPLES_DIR.exists()

    def test_all_tool_dirs_exist(self):
        for tool in KNOWN_TOOLS:
            assert (SAMPLES_DIR / tool).is_dir(), f"디렉터리 없음: {tool}"

    def test_all_tools_have_at_least_one_jpg(self):
        for tool in KNOWN_TOOLS:
            files = _jpeg_files(tool)
            assert len(files) >= 1, f"{tool}: JPEG 파일 없음"

    def test_readme_exists(self):
        assert (SAMPLES_DIR / "README.md").exists()

    def test_international_tools_have_multiple_samples(self):
        for tool in INTERNATIONAL_TOOLS:
            files = _jpeg_files(tool)
            assert len(files) >= 2, f"{tool}: 샘플 부족 (최소 2개)"


# ---------------------------------------------------------------------------
# 픽스처 유효성 검증
# ---------------------------------------------------------------------------

class TestFixtureValidity:
    @pytest.mark.parametrize("tool", KNOWN_TOOLS)
    def test_all_jpgs_are_valid(self, tool):
        for path in _jpeg_files(tool):
            img = Image.open(path)
            assert img.format == "JPEG", f"{path}: JPEG 아님"
            assert img.size[0] > 0 and img.size[1] > 0

    @pytest.mark.parametrize("tool", KNOWN_TOOLS)
    def test_all_jpgs_readable_as_rgb(self, tool):
        for path in _jpeg_files(tool):
            img = Image.open(path).convert("RGB")
            assert img.mode == "RGB"


# ---------------------------------------------------------------------------
# 도구별 메타데이터 패턴 검증
# ---------------------------------------------------------------------------

class TestStableDiffusionFixture:
    def test_has_jpeg_files(self):
        assert len(_jpeg_files("stable_diffusion")) >= 3

    def test_software_field_contains_stable_diffusion(self):
        for path in _jpeg_files("stable_diffusion"):
            exif = _exif(path)
            software = exif.get("0th", {}).get(piexif.ImageIFD.Software, b"")
            assert b"Stable Diffusion" in software, f"{path.name}: Software 필드 없음"

    def test_user_comment_present(self):
        for path in _jpeg_files("stable_diffusion"):
            exif = _exif(path)
            uc = exif.get("Exif", {}).get(piexif.ExifIFD.UserComment, b"")
            assert len(uc) > 0, f"{path.name}: UserComment 없음"

    def test_user_comment_has_ascii_prefix(self):
        for path in _jpeg_files("stable_diffusion"):
            exif = _exif(path)
            uc = exif.get("Exif", {}).get(piexif.ExifIFD.UserComment, b"")
            assert uc.startswith(b"ASCII\x00\x00\x00"), f"{path.name}: ASCII prefix 없음"


class TestComfyuiFixture:
    def test_has_jpeg_files(self):
        assert len(_jpeg_files("comfyui")) >= 2

    def test_software_field_is_comfyui(self):
        for path in _jpeg_files("comfyui"):
            exif = _exif(path)
            software = exif.get("0th", {}).get(piexif.ImageIFD.Software, b"")
            assert b"ComfyUI" in software

    def test_user_comment_contains_workflow_json(self):
        for path in _jpeg_files("comfyui"):
            exif = _exif(path)
            uc = exif.get("Exif", {}).get(piexif.ExifIFD.UserComment, b"")
            payload = uc[8:] if uc.startswith(b"ASCII\x00\x00\x00") else uc
            import json
            data = json.loads(payload.decode("ascii", errors="ignore"))
            assert "nodes" in data


class TestMidjourneyFixture:
    def test_has_jpeg_files(self):
        assert len(_jpeg_files("midjourney")) >= 2

    def test_no_ai_exif_software(self):
        """Midjourney는 Software 필드에 AI 생성 정보 없음."""
        for path in _jpeg_files("midjourney"):
            exif = _exif(path)
            software = exif.get("0th", {}).get(piexif.ImageIFD.Software, b"")
            assert b"Midjourney" not in software  # 메타데이터 없음

    def test_no_user_comment(self):
        for path in _jpeg_files("midjourney"):
            exif = _exif(path)
            uc = exif.get("Exif", {}).get(piexif.ExifIFD.UserComment)
            assert uc is None


class TestDalle3Fixture:
    def test_has_jpeg_files(self):
        assert len(_jpeg_files("dalle3")) >= 2

    def test_no_ai_metadata(self):
        for path in _jpeg_files("dalle3"):
            exif = _exif(path)
            software = exif.get("0th", {}).get(piexif.ImageIFD.Software, b"")
            uc = exif.get("Exif", {}).get(piexif.ExifIFD.UserComment)
            assert b"DALL-E" not in software
            assert uc is None


class TestFireflyFixture:
    def test_has_jpeg_files(self):
        assert len(_jpeg_files("firefly")) >= 2

    def test_software_is_adobe_firefly(self):
        for path in _jpeg_files("firefly"):
            exif = _exif(path)
            software = exif.get("0th", {}).get(piexif.ImageIFD.Software, b"")
            assert b"Adobe Firefly" in software

    def test_copyright_mentions_c2pa(self):
        """실제 Firefly는 C2PA 사용. 합성 픽스처는 Copyright 필드로 표시."""
        for path in _jpeg_files("firefly"):
            exif = _exif(path)
            copyright_field = exif.get("0th", {}).get(piexif.ImageIFD.Copyright, b"")
            assert b"C2PA" in copyright_field


class TestKoreanToolPlaceholders:
    @pytest.mark.parametrize("tool", KOREAN_TOOLS)
    def test_placeholder_files_exist(self, tool):
        files = _jpeg_files(tool)
        assert len(files) >= 1
        assert any("placeholder" in f.name for f in files)

    @pytest.mark.parametrize("tool", KOREAN_TOOLS)
    def test_placeholders_are_valid_jpeg(self, tool):
        for path in _jpeg_files(tool):
            img = Image.open(path)
            assert img.format == "JPEG"

    @pytest.mark.parametrize("tool", KOREAN_TOOLS)
    def test_placeholders_have_no_ai_metadata(self, tool):
        """한국 도구: 메타데이터 미확인 → 플레이스홀더는 plain JPEG."""
        for path in _jpeg_files(tool):
            exif = _exif(path)
            uc = exif.get("Exif", {}).get(piexif.ExifIFD.UserComment)
            assert uc is None, f"{path.name}: 플레이스홀더에 AI 메타 없어야 함"

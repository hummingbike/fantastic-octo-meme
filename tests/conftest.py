"""Shared pytest fixtures for KoAI-Verify tests."""

import io
from pathlib import Path

import piexif
import pytest
from PIL import Image

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _make_minimal_jpeg(path: Path) -> None:
    """Create a minimal 64x64 white JPEG."""
    img = Image.new("RGB", (64, 64), color=(255, 255, 255))
    img.save(path, format="JPEG", quality=95)


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def plain_jpeg(fixtures_dir: Path) -> Path:
    """Minimal JPEG with no metadata."""
    path = fixtures_dir / "plain.jpg"
    if not path.exists():
        _make_minimal_jpeg(path)
    return path


@pytest.fixture(scope="session")
def exif_ai_jpeg(fixtures_dir: Path) -> Path:
    """JPEG with EXIF UserComment set to AI disclosure text."""
    path = fixtures_dir / "exif_ai.jpg"
    if not path.exists():
        img = Image.new("RGB", (64, 64), color=(200, 220, 240))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        buf.seek(0)

        exif_dict: dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
        # UserComment: must be prefixed with 8-byte charset code (ASCII = b"ASCII\x00\x00\x00")
        user_comment = b"ASCII\x00\x00\x00AI Generated"
        exif_dict["Exif"][piexif.ExifIFD.UserComment] = user_comment
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = b"AI Generated Image"
        exif_bytes = piexif.dump(exif_dict)

        img2 = Image.open(buf)
        img2.save(path, format="JPEG", exif=exif_bytes)
    return path


@pytest.fixture(scope="session")
def visible_label_jpeg(fixtures_dir: Path) -> Path:
    """Minimal JPEG — represents an image with a visible 'AI 생성' label overlay."""
    path = fixtures_dir / "visible_label.jpg"
    if not path.exists():
        _make_minimal_jpeg(path)
    return path

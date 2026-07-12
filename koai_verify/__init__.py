"""KoAI-Verify: 한국 AI 기본법 제31조 표시 의무 검증 SDK."""

__version__ = "0.2.1"

from koai_verify.api import verify
from koai_verify.pipeline import (
    ImageCorruptedError,
    ImageLoadError,
    ImageNotFoundError,
    ImageTooLargeError,
    UnsupportedFormatError,
    UrlNotAllowedError,
)
from koai_verify.report.formatter import VerificationReport
from koai_verify.rules.models import Verdict, VerificationContext

__all__ = [
    "__version__",
    "verify",
    "ImageLoadError",
    "ImageNotFoundError",
    "UrlNotAllowedError",
    "UnsupportedFormatError",
    "ImageTooLargeError",
    "ImageCorruptedError",
    "VerificationReport",
    "Verdict",
    "VerificationContext",
]

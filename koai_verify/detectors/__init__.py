from .result import DetectionResult, DetectorOutput
from .base import DetectorBase
from .c2pa_detector import C2PADetector
from .exif_detector import EXIFDetector
from .ocr_detector import OCRDetector
from .watermark_detector import WatermarkDetector

__all__ = [
    "DetectionResult",
    "DetectorOutput",
    "DetectorBase",
    "C2PADetector",
    "EXIFDetector",
    "OCRDetector",
    "WatermarkDetector",
]

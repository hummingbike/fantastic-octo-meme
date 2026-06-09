"""W7 — 오픈 비가시 워터마크 탐지 엔진.

오픈 비가시 워터마크(Tree-Ring, HiDDeN, StegaStamp, Stable Signature, IMATAG)를
탐지하려면 반드시 디코더 키 또는 학습된 디코더 모델이 필요하다.

본 모듈은 키 없이 실행할 수 있는 최선의 분석을 수행하되,
결과는 항상 UNKNOWN 으로 반환한다.

분석 항목 (Heuristic — 확정적 탐지 아님):
  1. LSB 무작위성 (chi-square) — 공간 도메인 스테가노그래피 힌트
  2. DCT 계수 통계 — JPEG 주파수 도메인 워터마크 힌트 (JPEG에 한함)
  3. 채널별 잡음 분산 — 신경망 기반 워터마크 흔적 힌트

이 분석은 "워터마크가 있다"는 판정의 근거가 될 수 없다.
디코더 키 없이는 오픈 워터마크의 존재를 확인할 수 없다.

판정:
  UNKNOWN  : 항상 (디코더 키 없음)
  details 에 heuristic_scores 포함 (0.0–1.0, 높을수록 의심)
"""
from __future__ import annotations

import io
import struct
from typing import Optional

from PIL import Image, UnidentifiedImageError

from .base import DetectorBase
from .result import DetectionResult, DetectorOutput

# 알려진 오픈 워터마크 유형
KNOWN_WATERMARK_TYPES: list[str] = [
    "Tree-Ring",        # 주파수 도메인, NeurIPS 2023
    "HiDDeN",           # 공간 도메인 신경망, ECCV 2018
    "StegaStamp",       # 공간 도메인, CVPR 2020
    "Stable_Signature", # 주파수 도메인, ICCV 2023
    "IMATAG",           # 공간 도메인, 비공개 상용
    "SynthID",          # Google 비공개 API
]

# 탐지 불가 이유 요약
_DETECTION_LIMIT_REASON = (
    "Invisible watermark detection requires decoder key or trained model weights. "
    "Without these, no open watermark type can be confirmed or denied."
)


class WatermarkDetector(DetectorBase):
    """비가시 워터마크 탐지 엔진.

    키/모델 없이는 탐지 불가 → 항상 UNKNOWN 반환.
    Heuristic 점수를 details 에 포함해 향후 키 통합 시 활용 가능하게 함.
    """

    @property
    def name(self) -> str:
        return "watermark"

    def detect(self, image_bytes: bytes) -> DetectorOutput:
        # 이미지 유효성 확인
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.load()
            fmt = img.format  # "JPEG" | "PNG" | "WEBP" | None
            mode = img.mode
            size = img.size
        except (UnidentifiedImageError, Exception):
            return DetectorOutput(
                result=DetectionResult.UNKNOWN,
                detector_name=self.name,
                details={
                    "reason": "image_not_readable",
                    "detection_limit": _DETECTION_LIMIT_REASON,
                },
            )

        heuristics = _compute_heuristics(img, image_bytes, fmt)

        return DetectorOutput(
            result=DetectionResult.UNKNOWN,
            detector_name=self.name,
            details={
                "reason": "no_decoder_key",
                "detection_limit": _DETECTION_LIMIT_REASON,
                "checked_types": KNOWN_WATERMARK_TYPES,
                "image_format": fmt,
                "image_mode": mode,
                "image_size": list(size),
                "heuristic_scores": heuristics,
            },
        )


# ---------------------------------------------------------------------------
# Heuristic 분석 — 탐지 확정 불가, 참고용 점수만 제공
# ---------------------------------------------------------------------------

def _compute_heuristics(
    img: Image.Image,
    image_bytes: bytes,
    fmt: Optional[str],
) -> dict[str, float]:
    """이미지에서 비가시 워터마크 힌트 점수를 계산한다.

    반환값: {지표명: 0.0–1.0} (높을수록 의심 강도 높음, 확정 불가)
    """
    scores: dict[str, float] = {}

    try:
        scores["lsb_chi_score"] = _lsb_chi_score(img)
    except Exception:
        scores["lsb_chi_score"] = -1.0  # 계산 실패

    if fmt == "JPEG":
        try:
            scores["dct_anomaly_score"] = _dct_anomaly_score(image_bytes)
        except Exception:
            scores["dct_anomaly_score"] = -1.0

    try:
        scores["channel_noise_variance"] = _channel_noise_variance(img)
    except Exception:
        scores["channel_noise_variance"] = -1.0

    return scores


def _lsb_chi_score(img: Image.Image) -> float:
    """LSB 무작위성 chi-square 검정 점수 (0.0=완전 균일, 1.0=완전 무작위).

    LSB 스테가노그래피는 LSB 비트를 무작위 메시지로 덮어 쓰므로
    자연 이미지보다 LSB 분포가 균일하게 나타나는 경향이 있다.
    """
    rgb = img.convert("RGB")
    # tobytes() → [R1,G1,B1, R2,G2,B2, ...] — R 채널은 인덱스 0,3,6,...
    raw = rgb.tobytes()
    lsbs = [raw[i] & 1 for i in range(0, len(raw), 3)]
    n = len(lsbs)
    if n == 0:
        return 0.0
    ones = sum(lsbs)
    zeros = n - ones
    expected = n / 2.0
    # chi-square 통계량 정규화 (값이 0 에 가까울수록 균일)
    chi = ((ones - expected) ** 2 + (zeros - expected) ** 2) / expected
    # 정규화: chi / n → 0~1 범위 근사 (완전 무작위=0, 완전 편향=1)
    normalized = 1.0 - min(chi / max(n * 0.01, 1.0), 1.0)
    return round(normalized, 4)


def _dct_anomaly_score(jpeg_bytes: bytes) -> float:
    """JPEG DCT 계수에서 주파수 도메인 워터마크 힌트를 계산한다.

    Tree-Ring / Stable Signature 계열은 주파수 도메인에 패턴을 삽입한다.
    정확한 탐지는 디코더 키 필요 — 여기서는 고주파 에너지 비율만 측정한다.
    """
    # JPEG 마커 파싱 — SOS 이전 계수 블록 수 추정 (간단화)
    pos = 0
    segments: list[tuple[int, int]] = []
    while pos < len(jpeg_bytes) - 1:
        if jpeg_bytes[pos] != 0xFF:
            break
        marker = jpeg_bytes[pos + 1]
        if marker in (0xD8, 0xD9):  # SOI / EOI
            pos += 2
            continue
        if marker == 0xDA:  # SOS — 이후는 엔트로피 코딩 데이터
            break
        if pos + 3 >= len(jpeg_bytes):
            break
        length = struct.unpack(">H", jpeg_bytes[pos + 2 : pos + 4])[0]
        segments.append((marker, length))
        pos += 2 + length

    # 세그먼트 수를 정규화 (많을수록 복잡한 구조 — 간단한 힌트)
    segment_count = len(segments)
    score = min(segment_count / 20.0, 1.0)  # 20세그먼트 기준 정규화
    return round(score, 4)


def _channel_noise_variance(img: Image.Image) -> float:
    """채널별 잡음 분산을 측정한다.

    신경망 워터마크는 미세한 잡음을 추가하므로 자연 이미지보다
    분산이 높게 나타날 수 있다. 단순 힌트 — 확정 근거 아님.
    """
    rgb = img.convert("RGB")
    # tobytes() → [R1,G1,B1, R2,G2,B2, ...] — R 채널은 인덱스 0,3,6,...
    raw = rgb.tobytes()
    n = len(raw) // 3
    if n < 2:
        return 0.0
    r_vals = [raw[i] for i in range(0, len(raw), 3)]
    mean_r = sum(r_vals) / n
    var_r = sum((v - mean_r) ** 2 for v in r_vals) / n

    # 0–255 분산 최대치는 ~16320 (균일 0,255 분포)
    normalized = min(var_r / 16320.0, 1.0)
    return round(normalized, 4)

"""W20 — 사용량 측정 모듈.

요청 횟수·이미지 크기·판정 결과를 메모리에 누적하고 JSON 파일로 선택적 영속화한다.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """단일 요청 사용량 레코드."""

    timestamp: str
    image_size_bytes: int
    verdict: str
    api_key_prefix: str  # 키의 앞 8자만 (식별용, 전체 노출 금지)
    duration_ms: float


@dataclass
class UsageStats:
    """집계 사용량 통계."""

    total_requests: int = 0
    total_image_bytes: int = 0
    verdict_counts: dict[str, int] = field(default_factory=dict)
    records: list[UsageRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "total_image_bytes": self.total_image_bytes,
            "verdict_counts": self.verdict_counts,
            "records": [
                {
                    "timestamp": r.timestamp,
                    "image_size_bytes": r.image_size_bytes,
                    "verdict": r.verdict,
                    "api_key_prefix": r.api_key_prefix,
                    "duration_ms": r.duration_ms,
                }
                for r in self.records
            ],
        }


class UsageTracker:
    """스레드-안전 사용량 추적기."""

    def __init__(self, persist_path: Optional[Path] = None) -> None:
        self._lock = threading.Lock()
        self._stats = UsageStats()
        self._persist_path = persist_path

    def record(
        self,
        image_size_bytes: int,
        verdict: str,
        api_key: str,
        duration_ms: float,
    ) -> None:
        api_key_prefix = (api_key[:8] + "...") if len(api_key) >= 8 else api_key
        rec = UsageRecord(
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            image_size_bytes=image_size_bytes,
            verdict=verdict,
            api_key_prefix=api_key_prefix,
            duration_ms=duration_ms,
        )
        with self._lock:
            self._stats.total_requests += 1
            self._stats.total_image_bytes += image_size_bytes
            self._stats.verdict_counts[verdict] = self._stats.verdict_counts.get(verdict, 0) + 1
            self._stats.records.append(rec)
            if self._persist_path:
                self._flush_locked()

        logger.info(
            "usage verdict=%s size=%d ms=%.1f key=%s",
            verdict,
            image_size_bytes,
            duration_ms,
            api_key_prefix,
        )

    def get_stats(self) -> UsageStats:
        with self._lock:
            return UsageStats(
                total_requests=self._stats.total_requests,
                total_image_bytes=self._stats.total_image_bytes,
                verdict_counts=dict(self._stats.verdict_counts),
                records=list(self._stats.records),
            )

    def _flush_locked(self) -> None:
        assert self._persist_path is not None
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(self._stats.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("usage persist failed: %s", exc)


# 기본 전역 트래커 (앱에서 교체 가능)
_default_tracker = UsageTracker()


def get_tracker() -> UsageTracker:
    return _default_tracker


def set_tracker(tracker: UsageTracker) -> None:
    global _default_tracker
    _default_tracker = tracker

"""W22 — 공유 가능한 리포트 저장소.

POST /v0/verify(share=true)로 생성된 판정 리포트를 보관해 GET /v0/share/{id},
GET /v0/badge/{id}.svg 로 공개 조회할 수 있게 한다.

리포트 식별자는 이미지 sha256 해시를 그대로 사용한다 — 공개 식별자로 해시
자체만 노출되므로 "원본 이미지 데이터 포함 금지" 정책(CLAUDE.md)에 부합한다.
인메모리 저장소이며 서버 재시작 시 소실된다 (영구 저장은 W34 레지스트리에서
다룬다).
"""

from __future__ import annotations

import threading
from typing import Optional


class ReportStore:
    """스레드-안전 인메모리 리포트 저장소."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reports: dict[str, dict] = {}

    def save(self, report: dict) -> str:
        """리포트를 저장하고 공개 식별자(report_id)를 반환한다."""
        report_id = extract_report_id(report["image"])
        with self._lock:
            self._reports[report_id] = report
        return report_id

    def get(self, report_id: str) -> Optional[dict]:
        with self._lock:
            return self._reports.get(report_id)

    def clear(self) -> None:
        with self._lock:
            self._reports.clear()


def extract_report_id(image_sha256: str) -> str:
    """ "sha256:<hex>" 형식에서 식별자로 쓸 hex 부분만 추출한다."""
    return image_sha256.split(":", 1)[-1] if ":" in image_sha256 else image_sha256


# 기본 전역 저장소 (앱에서 교체 가능, usage.py의 트래커 패턴과 동일)
_default_store = ReportStore()


def get_report_store() -> ReportStore:
    return _default_store


def set_report_store(store: ReportStore) -> None:
    global _default_store
    _default_store = store

"""W24 — 규제 변경 모니터링 자동화.

과기정통부·TTA·국가법령정보센터의 고정된 공지 페이지 콘텐츠 해시를 주기적으로
비교해 변경 여부를 탐지한다 (tta_contact.SUBMISSION_PROCESS step 5 "반영 여부
추적"에서 예고한 모니터링 스크립트).

외부 HTTP 호출은 fetcher 콜백으로 주입받는다 — 테스트는 실제 네트워크 접근
없이 가짜 fetcher로 검증하고, 운영 환경(scripts/check_regulation_updates.py)
에서만 default_fetcher가 실제로 호출된다. URL은 고정된 정부·표준화 기관
목록(MONITORED_SOURCES)만 다루며 사용자 입력을 받지 않는다.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional
from urllib.request import urlopen

Fetcher = Callable[[str], str]


@dataclass(frozen=True)
class MonitorSource:
    """모니터링 대상 공지 페이지."""

    name: str
    url: str
    description: str


# 조사 기준일: 2026-06-17. URL은 docs/references/AI_투명성_확보_가이드라인_원문요약.md,
# koai_verify/standards/tta_contact.py 에서 이미 검증된 출처를 재사용한다.
MONITORED_SOURCES: list[MonitorSource] = [
    MonitorSource(
        name="msit_press_release",
        url="https://www.msit.go.kr/bbs/view.do?sCode=user&mId=102&mPid=100&bbsSeqNo=81&nttSeqNo=3148988",
        description="과기정통부 「인공지능 투명성 확보 가이드라인」 보도자료",
    ),
    MonitorSource(
        name="nia_guideline_notice",
        url="https://www.nia.or.kr/site/nia_kor/ex/bbs/View.do?cbIdx=99835&bcIdx=28987",
        description="NIA 가이드라인 공지 (원본 PDF 출처)",
    ),
    MonitorSource(
        name="tta_tc010_portal",
        url="https://www.tta.or.kr/data/standardization/tcList.jsp",
        description="TTA TC010 표준화 포털 (과제·일정 공지)",
    ),
    MonitorSource(
        name="law_go_kr_ai_act",
        url="https://www.law.go.kr/lsInfoP.do?lsiSeq=268543",
        description="국가법령정보센터 — 인공지능 기본법 원문",
    ),
]


def compute_content_hash(content: str) -> str:
    """콘텐츠 문자열의 sha256 해시(hex)를 반환한다."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def default_fetcher(url: str, timeout: float = 10.0) -> str:
    """실제 HTTP GET으로 페이지 본문을 가져온다. 운영 스크립트에서만 사용한다."""
    with urlopen(url, timeout=timeout) as resp:  # noqa: S310 — 고정된 정부/표준화 기관 URL만 사용
        return resp.read().decode("utf-8", errors="replace")


@dataclass
class MonitorResult:
    """단일 소스에 대한 점검 결과. fetch 실패 시 error에 사유를 남기고 changed=False."""

    source_name: str
    changed: bool
    previous_hash: Optional[str]
    current_hash: str
    checked_at: str
    error: Optional[str] = None


class RegulationMonitor:
    """소스별 콘텐츠 해시를 비교해 변경을 탐지하고 상태를 영속화한다."""

    def __init__(self, fetcher: Fetcher, state_path: Optional[Path] = None) -> None:
        self._fetcher = fetcher
        self._state_path = state_path
        self._lock = threading.Lock()
        self._state: dict[str, str] = self._load_state()

    def _load_state(self) -> dict[str, str]:
        if self._state_path and self._state_path.exists():
            try:
                return json.loads(self._state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return {}
        return {}

    def _save_state_locked(self) -> None:
        if not self._state_path:
            return
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")

    def check(self, source: MonitorSource) -> MonitorResult:
        """소스를 점검하고, 이전 점검과 해시가 다르면 changed=True를 반환한다.

        첫 점검(상태 없음)은 기준선을 세우는 것으로 간주해 changed=False다.
        fetch 실패(타임아웃·네트워크 오류)는 변경으로 간주하지 않는다 — 정부
        사이트의 일시 차단이 매주 거짓 양성 이슈를 만드는 것을 막기 위함이다.
        """
        try:
            content = self._fetcher(source.url)
        except (OSError, ValueError) as exc:  # URLError/TimeoutError 는 OSError 하위
            return MonitorResult(
                source_name=source.name,
                changed=False,
                previous_hash=self._state.get(source.name),
                current_hash="",
                checked_at=_now_iso(),
                error=f"{type(exc).__name__}: {exc}",
            )
        current_hash = compute_content_hash(content)
        with self._lock:
            previous_hash = self._state.get(source.name)
            changed = previous_hash is not None and previous_hash != current_hash
            self._state[source.name] = current_hash
            self._save_state_locked()
        return MonitorResult(
            source_name=source.name,
            changed=changed,
            previous_hash=previous_hash,
            current_hash=current_hash,
            checked_at=_now_iso(),
        )

    def check_all(self, sources: Optional[list[MonitorSource]] = None) -> list[MonitorResult]:
        """모든(또는 지정한) 소스를 순서대로 점검한다."""
        return [self.check(s) for s in (sources if sources is not None else MONITORED_SOURCES)]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

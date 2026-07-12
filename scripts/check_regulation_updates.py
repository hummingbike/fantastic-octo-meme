"""W24 규제 변경 모니터링 실행 스크립트.

과기정통부·TTA·국가법령정보센터 공지 페이지의 콘텐츠 해시를 점검해 이전
실행과 달라졌는지 확인한다. `.github/workflows/regulation_monitor.yml`에서
주기적으로 실행된다.

사용법:
    python scripts/check_regulation_updates.py

종료 코드:
    0 — 변경 없음 (또는 최초 실행으로 기준선 수립, fetch 실패 소스는 건너뜀)
    1 — 하나 이상의 소스에서 변경 감지
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from koai_verify.standards.regulation_monitor import (  # noqa: E402
    MONITORED_SOURCES,
    RegulationMonitor,
    default_fetcher,
)

STATE_PATH = ROOT / ".regulation_monitor_state.json"


def main() -> int:
    monitor = RegulationMonitor(fetcher=default_fetcher, state_path=STATE_PATH)
    results = monitor.check_all(MONITORED_SOURCES)

    changed = [r for r in results if r.changed]
    for r in results:
        if r.error:
            status = "FETCH_ERROR"
        elif r.changed:
            status = "CHANGED"
        else:
            status = "no change"
        detail = f" — {r.error}" if r.error else ""
        print(f"[{status}] {r.source_name} ({r.checked_at}){detail}")

    if changed:
        print(f"\n{len(changed)}개 소스에서 변경 감지됨:")
        for r in changed:
            print(f"  - {r.source_name}")
        return 1

    print("\n변경 없음.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

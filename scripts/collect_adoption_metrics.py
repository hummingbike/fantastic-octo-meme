"""W25 채택 지표 수집 스크립트.

PRD §5 성공 지표 중 공개 API로 측정 가능한 항목(GitHub ★·포크·이슈,
PyPI/npm 게시 여부)을 실측해 스냅샷 JSON으로 저장하고, 마일스톤 목표
대비 평가와 Q2 게이트 결과를 마크다운으로 출력한다.

사용법:
    python scripts/collect_adoption_metrics.py [--milestone W16|W40|W52] [--out PATH]

종료 코드:
    0 — 수집 성공 (일부 지표 UNKNOWN 포함 가능)
    1 — 모든 지표 수집 실패 (네트워크 차단 등)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from koai_verify.analysis.adoption_metrics import (  # noqa: E402
    collect_snapshot,
    default_fetcher,
    evaluate_q2_gate,
    evaluate_snapshot,
    format_snapshot_markdown,
)

DEFAULT_OUT = ROOT / "benchmarks" / "results" / "adoption_snapshot_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="PRD §5 채택 지표 실측")
    parser.add_argument("--milestone", default="W16", choices=["W16", "W40", "W52"])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    snapshot = collect_snapshot(default_fetcher)
    # W23 보류 상태 — 실연동 파트너 0곳은 저장소 사실 기반으로 확정 기록한다.
    snapshot.external_integrations = 0
    snapshot.paid_mrr_krw = 0
    snapshot.tta_status = "W19 컨택 조사·제안서 초안 완료, 제출은 수동 대기"

    measured = [snapshot.github_stars, snapshot.pypi_published, snapshot.npm_published]
    if all(v is None for v in measured):
        print("ERROR: 모든 지표 수집 실패 — 네트워크 상태를 확인하세요", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    assessments = evaluate_snapshot(snapshot, milestone=args.milestone)
    gate = evaluate_q2_gate(snapshot)
    print(format_snapshot_markdown(snapshot, assessments, gate, milestone=args.milestone))
    print(f"스냅샷 저장: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

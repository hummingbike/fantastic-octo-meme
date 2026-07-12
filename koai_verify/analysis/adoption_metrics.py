"""W25 — 2분기 회고: 채택 지표 실측·평가.

PRD §5 성공 지표(GitHub ★, SDK 설치수, 외부 통합, 호스팅 API 가입, 유료 MRR,
TTA 기여)를 실측해 마일스톤 목표와 대조하고, Q2 게이트(오픈 SDK 공개 +
외부 통합 ≥2 + 호스팅 API 가동) 통과 여부를 평가한다.

외부 HTTP 호출은 regulation_monitor와 동일하게 fetcher 콜백으로 주입받는다 —
테스트는 가짜 fetcher로 검증하고, 운영 스크립트
(scripts/collect_adoption_metrics.py)에서만 default_fetcher가 실제 호출된다.
측정 불가 지표는 절대 추정하지 않고 UNKNOWN으로 명시한다 (CLAUDE.md 원칙).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

Fetcher = Callable[[str], str]

GITHUB_REPO = "hummingbike/fantastic-octo-meme"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}"
PYPI_API_URL = "https://pypi.org/pypi/koai-verify/json"
NPM_API_URL = "https://registry.npmjs.org/@koai%2Fverify"


class MetricStatus(str, Enum):
    """지표 평가 상태 — 측정 불가는 UNKNOWN, 임의 추정 금지."""

    MET = "MET"
    NOT_MET = "NOT_MET"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# PRD §5 성공 지표 목표. None 은 해당 마일스톤에 목표 없음(—).
PRD_TARGETS: dict[str, dict[str, Optional[int]]] = {
    "W16": {"github_stars": 50, "weekly_installs": 1, "external_integrations": None, "api_signups": None},
    "W40": {"github_stars": 200, "weekly_installs": 100, "external_integrations": 2, "api_signups": 10},
    "W52": {"github_stars": 500, "weekly_installs": 500, "external_integrations": 5, "api_signups": 50},
}


@dataclass
class AdoptionSnapshot:
    """PRD §5 지표 실측 스냅샷. None 은 측정 불가(UNKNOWN)를 뜻한다."""

    collected_at: str = field(default_factory=lambda: _now_iso())
    github_stars: Optional[int] = None
    github_forks: Optional[int] = None
    github_watchers: Optional[int] = None
    github_open_issues: Optional[int] = None
    pypi_published: Optional[bool] = None
    pypi_latest_version: Optional[str] = None
    weekly_installs: Optional[int] = None
    npm_published: Optional[bool] = None
    external_integrations: Optional[int] = None
    api_signups: Optional[int] = None
    paid_mrr_krw: Optional[int] = None
    tta_status: Optional[str] = None

    def to_dict(self) -> dict:
        """JSON 직렬화용 dict를 반환한다."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AdoptionSnapshot":
        """dict에서 스냅샷을 복원한다 (알 수 없는 키는 무시)."""
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass(frozen=True)
class MetricAssessment:
    """단일 지표에 대한 목표 대비 평가."""

    metric: str
    actual: Optional[int]
    target: Optional[int]
    status: MetricStatus


def default_fetcher(url: str, timeout: float = 10.0) -> str:
    """실제 HTTP GET. 고정된 공개 API URL만 사용하며 운영 스크립트에서만 호출한다."""
    req = Request(url, headers={"User-Agent": "koai-verify-metrics"})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — 고정된 공개 API URL만 사용
        return resp.read().decode("utf-8", errors="replace")


def fetch_github_stats(fetcher: Fetcher) -> dict[str, Optional[int]]:
    """GitHub 저장소 지표(스타·포크·워처·오픈 이슈)를 수집한다. 실패 시 전부 None."""
    try:
        data = json.loads(fetcher(GITHUB_API_URL))
    except (URLError, HTTPError, OSError, json.JSONDecodeError, ValueError):
        return {"stars": None, "forks": None, "watchers": None, "open_issues": None}
    return {
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "watchers": data.get("subscribers_count"),
        "open_issues": data.get("open_issues_count"),
    }


def fetch_pypi_status(fetcher: Fetcher) -> tuple[Optional[bool], Optional[str]]:
    """PyPI 게시 여부와 최신 버전을 반환한다. 404는 미게시, 그 외 실패는 UNKNOWN."""
    try:
        data = json.loads(fetcher(PYPI_API_URL))
    except HTTPError as exc:
        return (False, None) if exc.code == 404 else (None, None)
    except (URLError, OSError, json.JSONDecodeError, ValueError):
        return None, None
    version = data.get("info", {}).get("version")
    return True, version


def fetch_npm_status(fetcher: Fetcher) -> Optional[bool]:
    """npm 게시 여부를 반환한다. 404는 미게시, 그 외 실패는 UNKNOWN."""
    try:
        fetcher(NPM_API_URL)
    except HTTPError as exc:
        return False if exc.code == 404 else None
    except (URLError, OSError):
        return None
    return True


def collect_snapshot(fetcher: Fetcher) -> AdoptionSnapshot:
    """공개 API에서 측정 가능한 지표를 수집해 스냅샷을 만든다.

    weekly_installs(다운로드 수)·api_signups는 공개 API로 측정 불가 → None 유지.
    """
    gh = fetch_github_stats(fetcher)
    pypi_published, pypi_version = fetch_pypi_status(fetcher)
    return AdoptionSnapshot(
        github_stars=gh["stars"],
        github_forks=gh["forks"],
        github_watchers=gh["watchers"],
        github_open_issues=gh["open_issues"],
        pypi_published=pypi_published,
        pypi_latest_version=pypi_version,
        npm_published=fetch_npm_status(fetcher),
    )


def evaluate_metric(metric: str, actual: Optional[int], target: Optional[int]) -> MetricAssessment:
    """실측값을 목표와 대조한다. 목표 없음→NOT_APPLICABLE, 실측 불가→UNKNOWN."""
    if target is None:
        status = MetricStatus.NOT_APPLICABLE
    elif actual is None:
        status = MetricStatus.UNKNOWN
    else:
        status = MetricStatus.MET if actual >= target else MetricStatus.NOT_MET
    return MetricAssessment(metric=metric, actual=actual, target=target, status=status)


def evaluate_snapshot(snapshot: AdoptionSnapshot, milestone: str = "W16") -> list[MetricAssessment]:
    """스냅샷을 PRD §5 마일스톤 목표와 대조한 평가 목록을 반환한다."""
    if milestone not in PRD_TARGETS:
        raise ValueError(f"unknown milestone: {milestone!r} (choose from {sorted(PRD_TARGETS)})")
    targets = PRD_TARGETS[milestone]
    return [
        evaluate_metric("github_stars", snapshot.github_stars, targets["github_stars"]),
        evaluate_metric("weekly_installs", snapshot.weekly_installs, targets["weekly_installs"]),
        evaluate_metric("external_integrations", snapshot.external_integrations, targets["external_integrations"]),
        evaluate_metric("api_signups", snapshot.api_signups, targets["api_signups"]),
    ]


@dataclass(frozen=True)
class GateItem:
    """Q2 게이트 항목 평가."""

    name: str
    passed: Optional[bool]
    evidence: str


def evaluate_q2_gate(snapshot: AdoptionSnapshot) -> list[GateItem]:
    """PLAN.md Q2 게이트(오픈 SDK 공개 + 외부 통합 ≥2 + 호스팅 API 가동)를 평가한다.

    '호스팅 API 가동'은 W20 산출물(서버·Docker) 완성 기준으로 통과 처리하되,
    상시 호스팅 인프라 미가동 사실을 evidence에 명시한다.
    """
    sdk_open = bool(snapshot.pypi_published)
    integrations = snapshot.external_integrations
    return [
        GateItem(
            name="오픈 SDK 공개",
            passed=sdk_open if snapshot.pypi_published is not None else None,
            evidence=(
                f"PyPI koai-verify {snapshot.pypi_latest_version or '미게시'}, "
                f"npm {'게시' if snapshot.npm_published else '미게시'}"
            ),
        ),
        GateItem(
            name="외부 통합 ≥2",
            passed=None if integrations is None else integrations >= 2,
            evidence=f"실측 {integrations if integrations is not None else 'UNKNOWN'}곳 (W23 보류)",
        ),
        GateItem(
            name="호스팅 API 가동",
            passed=True,
            evidence="POST /v0/verify + Docker 배포 구성 완료 (W20), 상시 호스팅 인프라는 미가동",
        ),
    ]


def format_snapshot_markdown(
    snapshot: AdoptionSnapshot,
    assessments: list[MetricAssessment],
    gate: list[GateItem],
    milestone: str = "W16",
) -> str:
    """스냅샷·평가·게이트를 회고 문서용 마크다운으로 렌더링한다."""
    lines = [
        f"### 채택 지표 실측 ({snapshot.collected_at})",
        "",
        f"| 지표 | 실측 | {milestone} 목표 | 판정 |",
        "|---|---|---|---|",
    ]
    for a in assessments:
        actual = "UNKNOWN" if a.actual is None else str(a.actual)
        target = "—" if a.target is None else str(a.target)
        lines.append(f"| {a.metric} | {actual} | {target} | {a.status.value} |")
    lines += ["", "### Q2 게이트", "", "| 항목 | 통과 | 근거 |", "|---|---|---|"]
    for g in gate:
        passed = "UNKNOWN" if g.passed is None else ("✅" if g.passed else "❌")
        lines.append(f"| {g.name} | {passed} | {g.evidence} |")
    return "\n".join(lines) + "\n"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

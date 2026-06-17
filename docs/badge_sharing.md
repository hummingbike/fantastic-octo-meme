# 공유 가능한 배지/리포트 — 바이럴 훅 (W22)

> 관련 코드: [`koai_verify/report/badge.py`](../koai_verify/report/badge.py),
> [`koai_verify/server/report_store.py`](../koai_verify/server/report_store.py)
> 관련 문서: [PLAN.md W23](../PLAN.md), [TODO.md](../TODO.md)

## 배경

PLG 전략(검증 먼저 → 개발자 채택)에서 가장 값싼 채택 채널은 사용자가 자발적으로
결과를 외부에 노출하는 것이다. shields.io·Codecov·Vercel의 "Deployed by" 배지처럼,
검증 결과를 README나 SNS에 박을 수 있는 작은 이미지(배지)와 공개 링크(리포트)를
제공하면 검증 자체가 광고가 된다. W22는 이 "공유 가능한 배지/리포트"를 호스팅
API(W20) 위에 얹는다.

## 동작 방식

```
POST /v0/verify (multipart, share=true)
  → 판정 리포트 생성 (기존 W10 포맷)
  → report_store에 저장, report_id = 이미지 sha256 해시
  → 응답에 report_id / share_url / badge_url 추가
```

- `GET /v0/share/{report_id}` — 인증 불필요. 저장된 판정 리포트(JSON) 전체를 반환한다.
- `GET /v0/badge/{report_id}.svg` — 인증 불필요. shields.io 스타일 flat SVG 배지를 반환한다.

`share=false`(기본값)이면 기존 `/v0/verify` 동작과 100% 동일하다 — 공유는
명시적 opt-in이다.

## 배지 임베드 예시

```markdown
[![KoAI-Verify](https://your-host/v0/badge/<report_id>.svg)](https://your-host/v0/share/<report_id>)
```

판정별 색상(`koai_verify.report.badge.badge_color`):

| Verdict | 색상 |
|---|---|
| COMPLIANT | `#4c1` (초록) |
| NON_COMPLIANT | `#e05d44` (빨강) |
| WARNING | `#dfb317` (노랑) |
| UNKNOWN | `#9f9f9f` (회색) |

## 설계 결정

- **존재하지 않는 report_id도 배지는 200을 반환한다** (UNKNOWN 회색으로 폴백).
  README/소셜 포스트에 박힌 이미지가 깨져 보이는 것을 피하기 위함 — shields.io와
  동일한 관례.
- **report_id = 이미지 sha256 해시**. 별도 토큰을 발급하지 않는 이유는 (1) 이미
  리포트에 해시가 들어 있어 추가 식별자를 만들 필요가 없고, (2) CLAUDE.md의
  "판정 리포트에 원본 이미지 데이터 포함 금지 (경로/해시만)" 원칙과 맞닿아 있다 —
  공개 식별자로 해시만 노출되므로 원본 이미지 데이터 유출이 없다.
- **공유 리포트에는 원본 이미지가 포함되지 않는다.** `VerificationReport`
  자체가 이미 해시만 담도록 설계되어 있어(W10), 공개 엔드포인트로 그대로
  노출해도 정책을 위반하지 않는다.

## 한계와 다음 단계

- `ReportStore`는 인메모리다 — 서버 재시작 시 모든 공유 리포트가 사라진다.
  영구 저장과 발급 기록은 W34(레지스트리 씨앗)에서 다룬다.
- 동일 이미지를 재검증하면 같은 `report_id`의 내용이 최신 리포트로 덮어써진다
  (멱등 — 별도 버전 관리는 하지 않는다).
- 리포트 보관 기간(가격 가설의 `report_retention_days`, W21)과의 연동은 아직
  없다 — 현재는 무제한 보관(프로세스 생존 기간 한정)이다.

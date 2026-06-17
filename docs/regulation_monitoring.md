# 규제 변경 모니터링 자동화 (W24)

> 관련 코드: [`koai_verify/standards/regulation_monitor.py`](../koai_verify/standards/regulation_monitor.py),
> [`scripts/check_regulation_updates.py`](../scripts/check_regulation_updates.py),
> [`.github/workflows/regulation_monitor.yml`](../.github/workflows/regulation_monitor.yml)
> 관련 문서: [tta_gap_analysis.md](tta_gap_analysis.md), [PLAN.md W25](../PLAN.md)

## 배경

표준은 형성 중이다(TTA TC010 계열). W19에서 TTA TC010에 갭 분석·제출 초안을
제출하는 프로세스를 정의했고(`koai_verify/standards/tta_contact.py`
`SUBMISSION_PROCESS`), 그 마지막 단계(step 5 "반영 여부 추적")는 "규제 변경
모니터링 스크립트"를 산출물로 예고했다. R-01~R-07 룰셋은 법령·가이드라인
원문(W1)을 근거로 확정했으므로, 원문이 바뀌면 룰셋도 따라가야 한다 — 이를
사람이 매주 직접 확인하는 대신 자동화한다.

## 동작 방식

```
MONITORED_SOURCES (고정 URL 4개)
  → RegulationMonitor.check_all()
  → 각 소스 페이지 본문을 가져와 sha256 해시 계산
  → 이전 실행 해시(.regulation_monitor_state.json)와 비교
  → 다르면 changed=True, 상태 파일 갱신
```

모니터링 대상(`MONITORED_SOURCES`):

| name | 설명 |
|---|---|
| `msit_press_release` | 과기정통부 「인공지능 투명성 확보 가이드라인」 보도자료 |
| `nia_guideline_notice` | NIA 가이드라인 공지 (원본 PDF 출처) |
| `tta_tc010_portal` | TTA TC010 표준화 포털 (과제·일정 공지) |
| `law_go_kr_ai_act` | 국가법령정보센터 — 인공지능 기본법 원문 |

이 URL들은 W1·W19에서 이미 검증된 출처(`docs/references/`,
`koai_verify/standards/tta_contact.py`)를 재사용한다 — 사용자 입력으로
URL을 받지 않으므로 SSRF 위험이 없다(고정 상수 목록).

## 자동화 (GitHub Actions)

`.github/workflows/regulation_monitor.yml`이 매주 월요일 00:00 UTC
(`workflow_dispatch`로 수동 실행도 가능)에 `scripts/check_regulation_updates.py`를
실행한다.

- 변경이 감지되면(`exit code 1`) `gh issue create`로 이슈를 자동 생성한다.
- 점검 상태(`.regulation_monitor_state.json`)는 저장소에 커밋해 다음 실행에서
  비교 기준으로 재사용한다.

## 한계

- **해시 비교는 "바뀌었다/안 바뀌었다"만 알려준다.** 무엇이 바뀌었는지는
  사람이 이슈를 열어 직접 확인해야 한다 — 의미 단위 diff는 다루지 않는다.
- **페이지 네트워크 오류도 "변경"으로 오인될 수 있다.** 정부 게시판이 일시
  접속 불가이거나 URL이 만료되면 fetch 자체가 예외를 던져 스크립트가 비정상
  종료한다(이 경우도 워크플로는 changed로 처리해 이슈를 띄운다) — 거짓
  양성을 줄이려면 추후 오류와 실제 변경을 구분하는 로직이 필요하다.
- **R-01~R-07 룰셋 갱신은 자동화 대상이 아니다.** 변경 감지 → 사람이 검토 →
  필요 시 `docs/rules/rule_engine_spec_v0.md`·룰 엔진 코드 수정의 흐름은
  여전히 수동이다. 이 자동화는 "검토할 시점을 알려주는 알람"이다.

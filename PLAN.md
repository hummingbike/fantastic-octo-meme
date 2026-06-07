# PLAN.md — KoAI-Verify 기술 구현 계획

> 기준일: 2026-06-06 (W1 시작)
> 전략 문서: [docs/AI컴플라이언스_1년차_기술선점_검증우선.md](docs/AI컴플라이언스_1년차_기술선점_검증우선.md)
> 제품 요건: [PRD.md](PRD.md)

---

## Phase 0 — 표준 정찰 & 벤치마크 정의 (W1–4, 2026.6)

목표: 선점 자산 1호인 강건성 벤치마크 프로토콜과 갭 리포트 초안 완성.

### W1: 법령·가이드라인 원문 정독 + 룰셋 초안

**목표 산출물**
- `docs/rules/rule_engine_spec_v0.md` — 제31조 판정 규칙 R-01~R-06 (PRD §4 기반)
- `docs/checklist_mapping.md` — 표시 의무 체크리스트 A~E → 룰 엔진 판정 규칙 이식

**작업**
1. 과기정통부 「AI 투명성 확보 가이드라인」 원문 정독
2. TTA 투명성 지침서 원문 정독
3. 제31조 ①고지 ②③표시 요건을 판정 가능한 조건문으로 변환
4. "비가시 마크만 있고 사람 인식 안내 없으면 불충족" 등 핵심 엣지 케이스 명시

### W2: 표시 포맷 지형 조사

**목표 산출물**
- `docs/format_landscape.md` — 탐지 가능/불가 포맷 경계 정의

**작업**
1. C2PA 매니페스트 구조 분석 (c2pa-python 라이브러리 평가)
2. SynthID류 탐지 가능성 조사 (공개 문헌 기준)
3. EXIF AI 플래그 표준 필드 목록 확정
4. 흔한 오픈 워터마크 패턴 조사
5. 가시 라벨 형태 조사 (한국어 "AI 생성" 텍스트 패턴)
6. 탐지 불가 케이스 → `UNKNOWN` 처리 방침 문서화

### W3: 강건성 벤치마크 설계 ★ 핵심

**목표 산출물**
- `benchmarks/protocol_v1.md` — 측정 프로토콜 (변형 배터리 × 탐지율 매트릭스)
- `benchmarks/transform_spec.py` — 변형 파라미터 코드 명세

**변형 배터리**
```
압축   : JPEG q=95/80/60/40/20, WebP q=90/70/50
리사이즈: 100%→75%→50%→25% (bilinear/bicubic)
크롭   : center 90%/70%, random 80%
재인코딩: Instagram 1080px/JPEG80, Twitter/X 1200px/WebP, KakaoTalk 프로필 시뮬
스크린샷: 96dpi/72dpi RGB 변환 시뮬
```

**매트릭스**: 포맷(C2PA/EXIF/가시라벨/워터마크) × 변형 × 탐지율(%)

### W4: 한국 이미지 도구 샘플 수집·분석

**목표 산출물**
- `docs/gap_report_draft.md` — 실제 도구 출력물 갭 리포트 초안
- `tests/fixtures/samples/` — 분석용 샘플 이미지 (저작권 클리어한 것만)

**대상 도구**: 드랩아트, GenApe, 벨라, 제디터 + 해외 주요 도구(Midjourney, DALL-E, Firefly)
**분석 항목**: 어떤 표시를 박는가 / 어떤 변형에서 깨지는가

**Phase 0 게이트**: 벤치마크 프로토콜 + 갭 리포트 초안 완성 → Phase 1 진행

---

## Phase 1 — 검증기 코어 (W5–13, 2026.7–8)

목표: CLI + Python SDK로 동작하는 검증기 v0 완성 + 오픈소스 공개 준비.

### W5: 인프라 골격

```
koai_verify/
  __init__.py
  detectors/
    base.py         # DetectorBase 추상 클래스
    result.py       # DetectionResult(FOUND/NOT_FOUND/UNKNOWN)
  rules/
    engine.py       # RuleEngine
    models.py       # Verdict(COMPLIANT/NON_COMPLIANT/WARNING/UNKNOWN)
  report/
    formatter.py    # JSON + 사람 읽기용 출력
  cli.py
tests/
pyproject.toml
.github/workflows/ci.yml
```

**작업**: 레포 초기화, CI 파이프라인(pytest + ruff + black), 입력 파이프라인(이미지 디코딩·포맷 정규화)

### W6: 탐지 엔진 ① — C2PA + EXIF

```python
# koai_verify/detectors/c2pa_detector.py
# koai_verify/detectors/exif_detector.py
```

- C2PA: c2pa-python 평가 후 채택 or 직접 파서
- EXIF: piexif/Pillow로 AI 관련 필드 추출 (UserComment, MakerNote, XMP 등)
- 각 탐지기: `detect(image_path) -> DetectionResult` 인터페이스

### W7: 탐지 엔진 ② — OCR + 워터마크

```python
# koai_verify/detectors/ocr_detector.py    (easyocr 기반, "AI 생성" 패턴)
# koai_verify/detectors/watermark_detector.py  (오픈 패턴)
```

### W8: 한국법 룰 엔진

```python
# koai_verify/rules/engine.py
# 입력: List[DetectionResult] → 출력: Verdict + 근거 규칙 목록
```

핵심 규칙: 비가시만 있고 사람 인식 안내 없으면 `NON_COMPLIANT` (R-03)

### W9: 강건성 하니스

```python
# koai_verify/robustness/harness.py
# transform(image, spec) → transformed_image
# run_battery(image_path, detector) → SurvivalReport
```

W3에서 설계한 변형 배터리 구현.

### W10: 판정 리포트 포맷 확정

```json
{
  "image": "hash:sha256:...",
  "verdict": "NON_COMPLIANT",
  "triggered_rules": ["R-03"],
  "detections": { "c2pa": "FOUND", "exif": "NOT_FOUND", "ocr": "FOUND", "watermark": "UNKNOWN" },
  "robustness": { "jpeg_q50": { "c2pa": 0.0, "ocr": 0.85 } },
  "recommendation": "비가시 워터마크가 발견됐으나 사람 인식 안내 텍스트가 없습니다. 가시 라벨 또는 UI 안내를 추가하세요.",
  "timestamp": "2026-08-01T00:00:00Z"
}
```

### W11: CLI v0

```bash
koai-verify image.jpg
koai-verify image.jpg --format json
koai-verify image.jpg --robustness  # 강건성 배터리 포함
```

### W12: Python/JS SDK + 웹 플레이그라운드

- `pip install koai-verify`
- `npm install @koai/verify`
- 웹 플레이그라운드: Gradio 또는 정적 HTML (드래그&드롭)

### W13: 오픈소스 공개 준비

- README (한/영), CONTRIBUTING.md, LICENSE(Apache-2.0)
- `docs/quickstart.md`
- `.github/ISSUE_TEMPLATE/`, `.github/workflows/`

---

## Q2 — 오픈 SDK 공개 · 개발자 채택 (W14–26, 2026.9–11)

| 주차 | 핵심 작업 |
|---|---|
| W14 | Phase 0 샘플 전체 → 검증기 실행 → 갭 리포트 확정 |
| W15 | 문서·예제 정비, GitHub Action (CI/CD 검증 통합) |
| W16 | **오픈 SDK + 강건성 벤치마크 공개** (Tistory·GitHub·GeekNews·디스콰이엇) |
| W17–18 | 채택 피드백 스프린트 (초기 통합 파트너 막힌 지점 해결) |
| W19 | TTA 표준화 참여 착수 (TC010, 검증 룰셋·벤치마크 의견 제출) |
| W20–21 | 호스팅 검증 API v0 (인증·API키·사용량 측정, 셀프서브) |
| W22 | 사용량 기반 가격 가설 설계 (무료↔유료 경계) |
| W23 | "공유 가능한 배지/리포트" — 바이럴 훅 |
| W24 | 통합 파트너 2~3곳 실연동 (협업, 영업 아님) |
| W25 | 규제 변경 모니터링 자동화 (과기정통부·TTA 공지 트래킹) |
| W26 | 2분기 회고 (채택 지표 점검) |

**Q2 게이트**: 오픈 SDK 공개 + 외부 통합 ≥2 + 호스팅 API 가동

---

## Q3 — 마커 + 폐루프 (W27–40, 2026.12–2027.2)

| 주차 | 핵심 작업 |
|---|---|
| W27–29 | 강건 비가시 워터마크 코어 (벤치마크로 생존율 측정 반복) |
| W30 | "사람 인식 안내" 자동 동반 모듈 + 가시 라벨 옵션 |
| W31 | 폐루프 완성: Verify → Mark → Re-verify |
| W32–33 | 마킹 성능·처리량 최적화 (비동기 큐, 대량 배치) |
| W34 | 레지스트리 씨앗 (발급 마크 로그·검증 가능 기록) |
| W35 | 폐루프 결과 공개 (채택·표준 영향력 강화 콘텐츠) |
| W36–37 | 플러그인/예제 확장 (Next.js, FastAPI, 이미지 생성 파이프라인) |
| W38 | 딥페이크 인접 강화 표시 분기 (가이드라인 W1 확정분 기준) |
| W39 | 호스팅 API 안정화 + 첫 유료 전환 제안 |
| W40 | 3분기 회고 (채택·API·첫 매출) |

**Q3 게이트**: 폐루프 동작 + 유료 고객 ≥1 + 레지스트리 가동

---

## Q4 — 감사·수익화 · 계도기간 캠페인 (W41–52, 2027.3–5)

| 주차 | 핵심 작업 |
|---|---|
| W41–42 | 감사 대시보드 (레지스트리 위: 증빙·CSV, 과태료 방어 유료 티어) |
| W43 | 계도기간 종료 캠페인 (~2027.1 이후, 시한성 메시지) |
| W44–45 | 영상·오디오 검증 프로토타입 (모서리 워터마크/자막/안내 멘트) |
| W46 | 엔터프라이즈/플랫폼 API 가설 |
| W47–49 | 채택·갱신 관리, 표준 변경 대응 고도화 |
| W50 | 재무·지표 점검, 2년차 MRR 역산 |
| W51 | 2년차 로드맵 초안 (영상/오디오 본격화 vs 레지스트리 강화 vs 표준 공식화) |
| W52 | 1년차 종합 회고 문서화 |

---

## 기술 의사결정 로그

| 날짜 | 결정 | 이유 |
|---|---|---|
| 2026-06-06 | 검증기 먼저, 마커 Q3 | 검증기는 standalone 가치. 채택 전에 마커는 과잉 |
| 2026-06-06 | Python 코어 + JS 래퍼 | 이미지 처리 생태계 + 웹 개발자 채택 |
| 2026-06-06 | Apache-2.0 라이선스 | 기업 채택 친화적 |
| 2026-06-06 | mock 테스트 금지 | 실제 포맷 파싱은 픽스처로만 검증 |

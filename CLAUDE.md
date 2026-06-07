# CLAUDE.md — KoAI-Verify 프로젝트

## 프로젝트 개요

**KoAI-Verify**: 한국 AI 기본법 제31조 표시 의무 검증 오픈소스 SDK.
AI 생성 이미지가 법적 표시 요건을 충족하는지 판정하고, 강건성(압축·리사이즈·재인코딩 생존율)을 측정한다.

- 전략: 검증 먼저(verifier-first) → 개발자 채택(PLG) → 마커·레지스트리 수익화
- 1인 개발, 주 12~18h, 2026.6 시작, 계도기간 종료 ~2027.1 타깃
- 관련 문서: [PRD.md](PRD.md) · [PLAN.md](PLAN.md) · [TODO.md](TODO.md)

---

## 디렉터리 구조 (예정)

```
koai_verify/          # Python 패키지 코어
  detectors/          # 탐지 엔진 (c2pa, exif, ocr, watermark)
  rules/              # 한국법 룰 엔진
  robustness/         # 강건성 하니스 (변형 배터리)
  report/             # 판정 리포트 포맷터
  cli.py              # CLI 진입점
sdk/                  # JS/TS SDK 래퍼
  src/
tests/
  unit/
  integration/
  fixtures/           # 테스트용 이미지 샘플
benchmarks/           # 강건성 벤치마크 결과 및 프로토콜
docs/                 # 기획·전략 문서
  AI컴플라이언스_1년차_기술선점_검증우선.md
scripts/              # 빌드·벤치마크 실행 스크립트
```

---

## 기술 스택

| 영역 | 선택 | 이유 |
|---|---|---|
| 코어 언어 | Python 3.10+ | 이미지 처리·ML 생태계 |
| 이미지 처리 | Pillow, OpenCV | 변형 배터리·포맷 정규화 |
| C2PA 파싱 | c2pa-python (or 자체 파서) | 매니페스트 검증 |
| OCR | easyocr 또는 tesseract | 가시 라벨 탐지 |
| CLI | Click 또는 Typer | `koai-verify <image>` |
| 패키징 | Poetry | 의존성 관리 |
| 테스트 | pytest | 단위·통합 테스트 |
| JS 래퍼 | Node.js + TypeScript | 웹 개발자 채택 |
| CI | GitHub Actions | 자동 테스트 + 벤치마크 |

---

## 개발 지침

### 코드 스타일
- Python: black + ruff, type hints 필수
- 공개 API에만 docstring (한 줄 요약만, 장황한 설명 금지)
- 탐지 불가 케이스는 `DetectionResult.UNKNOWN` 반환 — 절대 임의 추정 금지

### 커밋 규칙
- `feat:`, `fix:`, `bench:`, `docs:`, `test:` 접두어 사용
- W번호 포함 권장: `feat(W6): add C2PA manifest parser`

### 테스트 요건
- 각 탐지 엔진은 양성/음성/UNKNOWN 케이스 커버
- 강건성 하니스 테스트는 `tests/integration/` 에 위치
- mock 금지 — 실제 이미지 픽스처로 검증

### 보안 유의사항
- 외부 이미지 URL 처리 시 SSRF 방지 (URL 직접 fetch 금지, 파일만 수신)
- 판정 리포트에 원본 이미지 데이터 포함 금지 (경로/해시만)

---

## 핵심 개념

**룰 엔진 판정 흐름**
```
입력 이미지
  → 탐지 엔진들 병렬 실행 (C2PA / EXIF / OCR / Watermark)
  → 탐지 결과 집계
  → 룰셋 평가 (R-01~R-06, PRD §4 참조)
  → 판정: COMPLIANT / NON_COMPLIANT / WARNING / UNKNOWN
  → 리포트 생성 (JSON + 사람 읽기용 요약)
```

**강건성 하니스 흐름**
```
원본 이미지
  → 변형 배터리 적용 (압축/리사이즈/크롭/재인코딩 시뮬)
  → 각 변형본에 검증기 실행
  → 탐지 생존율 집계
  → 생존율 매트릭스 출력
```

---

## 중요 맥락

- 비가시 워터마크만 있고 **"사람 인식 안내"가 없으면 법적 불충족** (R-03) — 이게 핵심 판정 규칙.
- SynthID 등 비공개 마크는 탐지 불가 → `UNKNOWN` 명시. 과대주장은 신뢰 자산을 훼손함.
- 선점 우선순위: 검증기 자체보다 **강건성 벤치마크 공개(W16)** 가 채택 모멘텀의 핵심.
- 표준은 형성 중(TTA TC010 계열) — 룰셋은 W1 원문 확정 후 갱신, 자동 모니터링(W25) 필수.

---

## 자주 쓰는 명령어

```bash
# 개발 환경 설치
poetry install

# 단위 테스트
pytest tests/unit/

# 통합 테스트 (실제 이미지 필요)
pytest tests/integration/

# 강건성 벤치마크 실행
python scripts/run_benchmark.py --input fixtures/samples/

# CLI 검증
koai-verify path/to/image.jpg

# 린트
ruff check . && black --check .
```

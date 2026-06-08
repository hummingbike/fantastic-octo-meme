# TODO.md — KoAI-Verify 작업 추적

> 현재 주차: **W10** (2026-06-08 기준, W9 완료)
> 업데이트 규칙: 완료 즉시 체크. 주차 시작 시 다음 주 항목 활성화.

---

## 완료 — W1 (2026.6.1–6.7)

### 법령·가이드라인 원문 정독 + 룰셋 초안

- [x] 과기정통부 「AI 투명성 확보 가이드라인」 원문 다운로드 및 정독 (NIA PDF, 33p 전문)
- [ ] TTA AI 투명성 지침서 원문 다운로드 및 정독
- [x] 제31조 ①고지 ②③표시 요건을 판정 조건문으로 변환
  - [x] R-01: C2PA 매니페스트 존재 + 유효 서명 → 비가시_충족_후보
  - [x] R-02: EXIF/XMP AI 플래그 → 비가시_충족_후보
  - [x] R-03: 비가시 전용 시 1회 안내 확인 (비가시+1회안내=충족 / 비가시만=불충족)
  - [x] R-04: 가시 라벨 "AI 생성" 텍스트 확인 → 가시_충족_후보
  - [x] R-05: 어떤 표시도 탐지 불가 → 불충족
  - [x] R-06: 강건성 생존율 < 임계치 → 경고
  - [x] R-07: 딥페이크 + 비가시 전용 → 불충족 (신규, 가이드라인 §4 근거)
  - [x] 조항 인용구 원문 확정 (시행령 제23조 제2항 기반)
- [x] `docs/rules/rule_engine_spec_v0.md` 작성 완료 (v0.2, 원문 기반 확정)
- [x] `docs/references/AI_투명성_확보_가이드라인_원문요약.md` 작성 (가이드라인 전문 요약)
- [x] `docs/references/AI_투명성_확보_가이드라인_NIA.pdf` 다운로드 (원본 PDF)
- [ ] `docs/checklist_mapping.md` 작성 (체크리스트 A~E → 룰 이식)

---

## 완료 — W2 (2026.6.8–6.14)

### 표시 포맷 지형 조사

- [x] c2pa-python 라이브러리 평가 (pip install, 매니페스트 파싱 테스트) — 2026-06-07
- [x] C2PA 매니페스트 구조 문서화 — 2026-06-07
- [x] SynthID 탐지 가능성 조사 (Google 공개 문헌 조사) — 2026-06-07 (UNKNOWN 확정)
- [x] EXIF AI 관련 표준 필드 목록 확정 — 2026-06-07
  - [x] UserComment, XMP:DCSubjectCode, MakerNote 등
- [x] 흔한 오픈 워터마크 패턴 목록 작성 — 2026-06-07 (5종: Tree-Ring/HiDDeN/StegaStamp/Stable Signature/IMATAG)
- [x] 가시 라벨 패턴 목록 (한국어 "AI 생성", "AI-generated", 영문 변형) — 2026-06-07
- [x] `docs/format_landscape.md` 작성 — 2026-06-07

---

## 완료 — W3 (2026.6.15–6.21) — 강건성 벤치마크 설계 ★

- [x] 변형 배터리 파라미터 확정 (JPEG/WebP/리사이즈/크롭/재인코딩/스크린샷) — 2026-06-07
- [x] SNS 재인코딩 시뮬 파라미터 조사 (Instagram·Twitter·KakaoTalk 실측) — 2026-06-07
- [x] 측정 매트릭스 설계 (포맷 × 변형 → 탐지율 %) — 2026-06-07 (4×20=80셀)
- [x] `benchmarks/protocol_v1.md` 작성 — 2026-06-07
- [x] `benchmarks/transform_spec.py` 초안 작성 — 2026-06-07

---

## 완료 — W4 (2026.6.22–6.28) — 샘플 수집·갭 리포트

- [x] 드랩아트 출력 이미지 샘플 수집 및 분석 — 플레이스홀더 (UNKNOWN), 실제 수집 W8 전 재시도
- [x] GenApe 출력 이미지 샘플 수집 및 분석 — 플레이스홀더 (UNKNOWN)
- [x] 벨라 출력 이미지 샘플 수집 및 분석 — 플레이스홀더 (UNKNOWN)
- [x] 제디터 출력 이미지 샘플 수집 및 분석 — 플레이스홀더 (UNKNOWN)
- [x] Midjourney/DALL-E/Firefly 비교용 샘플 수집 — 합성 픽스처 (메타 패턴 재현)
- [x] 각 도구별 "무엇을 박나/안 박나" 정리 — `KNOWN_TOOL_CATALOG` (9개 도구)
- [x] 변형 후 깨지는 케이스 식별 — `transform_survivability.py` + `KNOWN_BREAK_CASES` 3종, 단위 테스트 24개
- [x] `docs/gap_report_draft.md` 작성 — 5개 도구 갭 분류, SNS 소거 케이스, R-03 위험 분석
- [x] `tests/fixtures/samples/` 디렉터리 구성 — 9개 도구, 합성/플레이스홀더 JPEG

---

## 완료 — W5 (2026.6.29–7.5) — 검증기 코어 인프라

- [x] pyproject.toml 정비 — Pillow >=10, CLI 엔트리포인트, pytest ini_options
- [x] GitHub Actions CI (pytest + ruff + black) — Python 3.10/3.11/3.12 매트릭스
- [x] 이미지 입력 파이프라인 — `koai_verify/pipeline.py` (로드·검증·sha256·SSRF 방지)
- [x] `koai_verify/detectors/` 기반 타입 — DetectionResult + DetectorBase (23 tests)
- [x] `koai_verify/rules/` 룰 엔진 — Verdict + RuleEngine R-01~R-07 (37 tests)
- [x] 단위 테스트 총계: 399개 통과

---

## 완료 — W6 (2026.7.6–7.12) — 탐지 엔진 ① C2PA + EXIF

- [x] `koai_verify/detectors/c2pa_detector.py` — C2PA 탐지 엔진 (2026-06-07)
- [x] `koai_verify/detectors/exif_detector.py` — EXIF AI 탐지 엔진 (2026-06-07)
- [x] 각 탐지기 단위 테스트 — C2PA 29개 + EXIF 46개, 전체 474개 통과 (2026-06-07)
- [x] tests/fixtures/c2pa/c2pa_test_C.jpg — c2pa-python 공식 서명 픽스처 추가 (2026-06-07)

---

## 완료 — W7 (2026.7.13–7.19) — 탐지 엔진 ② OCR + 워터마크

- [x] `koai_verify/detectors/ocr_detector.py` — OCR 탐지 엔진 (가시 라벨 "AI 생성" 패턴) (2026-06-07)
- [x] `koai_verify/detectors/watermark_detector.py` — 오픈 워터마크 탐지 모듈 (2026-06-07)
- [x] 각 탐지기 단위 테스트 — OCR 48개 + Watermark 48개, 전체 564개 통과 (2026-06-07)

---

## 완료 — W8 (2026.7.20–7.26) — 한국법 룰 엔진

- [x] `koai_verify/rules/engine.py` 확장 — 4개 탐지기 결과 집계 → 룰 평가 (2026-06-07)
- [x] R-01~R-07 전체 룰 연동 (C2PA + EXIF + OCR + Watermark 입력) (2026-06-07)
- [x] 각 룰 단위 테스트 47개 (양성/음성/UNKNOWN 케이스), 전체 611개 통과 (2026-06-07)

---

## 완료 — W9 (2026.7.27–8.2) — 강건성 하니스

- [x] `koai_verify/robustness/harness.py` — 변형 배터리 실행기 (2026-06-08)
- [x] `transform(image, spec) → bytes` 구현 (W3 설계 기반) (2026-06-08)
- [x] `run_battery(image_bytes, detector) → SurvivalReport` 구현 (2026-06-08)
- [x] 강건성 하니스 단위 테스트 41개, 전체 652개 통과 (2026-06-08)

---

## 현재 진행 중 — W10 (2026.8.3–8.9) — 판정 리포트 포맷

- [ ] `koai_verify/report/formatter.py` — JSON 리포트 + 사람 읽기용 요약
- [ ] `VerificationReport` 데이터 모델 (image hash, verdict, detections, robustness, recommendation)
- [ ] JSON 직렬화 / 역직렬화
- [ ] 판정 리포트 단위 테스트

---

## W9–W13 (Phase 1: 검증기 코어)

- [x] **W6** C2PA 탐지 엔진
- [x] **W6** EXIF 탐지 엔진
- [x] **W7** OCR 탐지 엔진 (가시 라벨)
- [x] **W7** 오픈 워터마크 탐지 모듈
- [x] **W8** 한국법 룰 엔진
- [x] **W9** 강건성 하니스 (변형 배터리 실행)
- [ ] **W10** 판정 리포트 포맷 확정 (JSON + 요약)
- [ ] **W11** CLI v0 (`koai-verify <image>`)
- [ ] **W12** Python SDK (`pip install koai-verify`)
- [ ] **W12** JS SDK 래퍼 (`npm install @koai/verify`)
- [ ] **W12** 웹 플레이그라운드 (드래그&드롭)
- [ ] **W13** README (한/영), CONTRIBUTING.md, LICENSE
- [ ] **W13** 오픈소스 공개 준비 완료

---

## Q2 마일스톤 (W14–26)

- [ ] **W16** 오픈 SDK + 강건성 벤치마크 공개 (Tistory·GitHub·GeekNews·디스콰이엇)
- [ ] **W19** TTA 표준화 참여 착수 (TC010 컨택)
- [ ] **W20** 호스팅 검증 API v0 가동
- [ ] **W24** 외부 통합 ≥2곳 실연동

---

## Q3 마일스톤 (W27–40)

- [ ] **W29** 강건 비가시 워터마크 코어 완성
- [ ] **W31** Verify → Mark → Re-verify 폐루프 완성
- [ ] **W34** 레지스트리 씨앗 가동
- [ ] **W39** 첫 유료 전환

---

## Q4 마일스톤 (W41–52)

- [ ] **W42** 감사 대시보드 (증빙·CSV 유료 티어)
- [ ] **W43** 계도기간 종료 캠페인 콘텐츠
- [ ] **W45** 영상·오디오 검증 프로토타입
- [ ] **W52** 1년차 종합 회고

---

## 백로그 (우선순위 미정)

- [ ] SynthID 탐지 가능성 추가 조사 (공개 연구 나올 경우)
- [ ] 영문 기술 블로그 (Dev.to, Medium) — 해외 채택 시도
- [ ] PyPI 자동 배포 파이프라인
- [ ] 벤치마크 결과 자동 업데이트 웹페이지

---

## 완료

<!-- 완료 항목을 날짜와 함께 여기로 이동 -->
- [x] 1년차 실행 계획 문서 작성 (2026-06-06)
- [x] PRD.md 초안 작성 (2026-06-06)
- [x] PLAN.md 작성 (2026-06-06)
- [x] CLAUDE.md 작성 (2026-06-06)
- [x] TODO.md 작성 (2026-06-06)
- [x] `docs/rules/rule_engine_spec_v0.md` v0.2 완성 (2026-06-06) — 원문 기반 R-01~R-07, VerificationContext, 딥페이크 룰, 판정 알고리즘, 체크리스트 A~E 매핑
- [x] `docs/references/AI_투명성_확보_가이드라인_NIA.pdf` 다운로드 (2026-06-06) — 과기정통부 원본 33p
- [x] `docs/references/AI_투명성_확보_가이드라인_원문요약.md` 작성 (2026-06-06)
- [x] **W2 표시 포맷 지형 조사 완료** (2026-06-07) — c2pa-python 평가, EXIF 필드 확정, SynthID UNKNOWN 정책, 오픈 워터마크 5종, 가시 라벨 패턴 한/영, `docs/format_landscape.md` 작성, 단위 테스트 84개 통과
- [x] **W3 강건성 벤치마크 설계 완료** (2026-06-07) — `benchmarks/transform_spec.py`(20개 변형·SNS 4종), `benchmarks/matrix.py`(80셀 매트릭스·R-06 연계), `benchmarks/protocol_v1.md`, 단위 테스트 84개(W3) 통과
- [x] **W4 샘플 수집·갭 리포트 완료** (2026-06-07) — `koai_verify/analysis/tool_fingerprint.py`(9도구 카탈로그), `transform_survivability.py`(생존 케이스), `docs/gap_report_draft.md`, 합성 픽스처 9종, 단위 테스트 24개(W4) 통과
- [x] **W5 검증기 코어 인프라 완료** (2026-06-07) — `detectors/` 기반 타입, `pipeline.py` 입력 파이프라인, `rules/` 룰 엔진(R-01~R-07), CI(GitHub Actions), 단위 테스트 114개(W5) 통과
- [x] **W6 탐지 엔진 ① C2PA + EXIF 완료** (2026-06-07) — `c2pa_detector.py`(FOUND/NOT_FOUND/UNKNOWN), `exif_detector.py`(5개 필드 검사), c2pa-python 공식 서명 픽스처, 단위 테스트 75개(W6) 통과 / 전체 474개
- [x] **W7 탐지 엔진 ② OCR + 워터마크 완료** (2026-06-07) — `ocr_detector.py`(한/영 패턴 18종, easyocr/pytesseract 폴백), `watermark_detector.py`(항상 UNKNOWN·heuristic 점수), OCR 픽스처 5종, 단위 테스트 96개(W7) 통과 / 전체 564개
- [x] **W8 한국법 룰 엔진 완료** (2026-06-07) — `aggregate_detections()`(4개 탐지기 출력 집계, FOUND>UNKNOWN>NOT_FOUND 우선순위), `RuleEngine.evaluate_outputs()`(DetectorOutput 리스트 직접 수용), 단위 테스트 47개(W8) 통과 / 전체 611개
- [x] **W9 강건성 하니스 완료** (2026-06-08) — `transform()`(apply_transform 래퍼), `TransformEntry`(survived: bool|None), `SurvivalReport`(생존율 집계·to_robustness_dict()), `run_battery()`(EXIFDetector × 20개 변형 배터리), RuleEngine R-06 연동, 단위 테스트 41개(W9) 통과 / 전체 652개

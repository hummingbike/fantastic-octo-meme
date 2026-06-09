# KoAI-Verify 아키텍처 / Architecture

이 문서는 KoAI-Verify 검증기의 내부 구조와 룰 평가 흐름을 설명합니다.

---

## 전체 구조 / System Overview

```
입력 레이어          탐지 레이어               룰 레이어           출력 레이어
──────────────    ──────────────────────    ──────────────    ──────────────
                  ┌─────────────────────┐
                  │  C2PADetector       │ → FOUND/NOT_FOUND
                  │  (c2pa_detector.py) │   /UNKNOWN
                  └─────────────────────┘
                  ┌─────────────────────┐
image.jpg/png ──▶ │  EXIFDetector       │ → FOUND/NOT_FOUND  ┌──────────────┐
  (pipeline.py)   │  (exif_detector.py) │   /UNKNOWN         │              │
  - 포맷 정규화   └─────────────────────┘         │           │  RuleEngine  │──▶ VerificationReport
  - SHA-256 계산  ┌─────────────────────┐          ├──────────▶│  (engine.py) │    (formatter.py)
  - SSRF 방지     │  OCRDetector        │ → FOUND/ │           │  R-01~R-07   │
                  │  (ocr_detector.py)  │   NOT_FOUND         │              │
                  └─────────────────────┘         │           └──────────────┘
                  ┌─────────────────────┐          │
                  │  WatermarkDetector  │ → UNKNOWN│
                  │  (watermark_det.py) │          │
                  └─────────────────────┘

[선택] 강건성 하니스 (robustness/harness.py)
  원본 이미지 → 변형 배터리(20개) → 각 변형본 탐지기 실행 → 생존율 집계 → R-06 입력
```

---

## 컴포넌트 상세 / Component Details

### 1. 입력 파이프라인 (`koai_verify/pipeline.py`)

```
이미지 경로 입력
  │
  ├─ 파일 존재 확인
  ├─ 포맷 검증 (JPEG/PNG/WebP/TIFF/BMP)
  ├─ SHA-256 해시 계산 (리포트용 식별자)
  └─ PIL Image 객체 반환
```

- URL 직접 fetch 금지 (SSRF 방지) — 파일 경로만 수신
- 지원 포맷: JPEG, PNG, WebP, TIFF, BMP

### 2. 탐지 엔진 (`koai_verify/detectors/`)

| 탐지기 | 파일 | 탐지 대상 | 반환값 |
|---|---|---|---|
| C2PADetector | `c2pa_detector.py` | C2PA 매니페스트 + 서명 | FOUND / NOT_FOUND / UNKNOWN |
| EXIFDetector | `exif_detector.py` | EXIF/XMP AI 플래그 (5개 필드) | FOUND / NOT_FOUND / UNKNOWN |
| OCRDetector | `ocr_detector.py` | 가시 라벨 "AI 생성" 텍스트 (18개 패턴) | FOUND / NOT_FOUND / UNKNOWN |
| WatermarkDetector | `watermark_detector.py` | 오픈 워터마크 패턴 (Tree-Ring 등) | UNKNOWN (탐지 불가 명시) |

모든 탐지기는 `DetectorBase` 를 상속하며 `detect(image) → DetectionResult` 인터페이스를 구현합니다.

### 3. 룰 엔진 (`koai_verify/rules/`)

```python
# 집계 우선순위: FOUND > UNKNOWN > NOT_FOUND
aggregate_detections([c2pa, exif, ocr, watermark]) → AggregatedResult
  └─ invisible: FOUND/UNKNOWN/NOT_FOUND  (C2PA + EXIF 결합)
  └─ visible:   FOUND/UNKNOWN/NOT_FOUND  (OCR 결과)

RuleEngine.evaluate(aggregated) → Verdict + triggered_rules
```

### 4. 룰셋 흐름 / Rule Flow

```
AggregatedResult
  │
  ├─ R-01: invisible == FOUND          → 비가시_충족_후보
  ├─ R-02: exif == FOUND               → 비가시_충족_후보
  ├─ R-03: invisible_only AND no_visible → NON_COMPLIANT ★ 핵심 룰
  ├─ R-04: visible == FOUND            → 가시_충족_후보 → COMPLIANT
  ├─ R-05: all NOT_FOUND               → NON_COMPLIANT
  ├─ R-06: robustness_rate < threshold → WARNING
  └─ R-07: deepfake AND invisible_only → NON_COMPLIANT
```

**R-03 핵심 판정 규칙**: 비가시 워터마크(C2PA/EXIF)만 존재하고 가시 라벨("AI 생성" 텍스트)이 없으면 `NON_COMPLIANT`. 한국 AI 기본법 제31조 + 과기정통부 가이드라인 §4 기반.

### 5. 강건성 하니스 (`koai_verify/robustness/`)

```
원본 이미지
  │
  ├─ JPEG 압축: q=95/80/60/40/20
  ├─ WebP 압축: q=90/70/50
  ├─ 리사이즈:  75%/50%/25% (bilinear/bicubic)
  ├─ 크롭:     center 90%/70%, random 80%
  ├─ SNS 재인코딩: Instagram(1080px/JPEG80) · Twitter(1200px/WebP)
  │              KakaoTalk · 스크린샷 시뮬
  └─ 각 변형본 → EXIFDetector 실행 → survived: bool
      → SurvivalReport(survival_rate, per_transform)
      → R-06 입력 (survival_rate < 0.5 → WARNING)
```

변형 배터리: 총 20개 / 지원 포맷: 4종 (C2PA/EXIF/가시라벨/워터마크)

### 6. 판정 리포트 (`koai_verify/report/formatter.py`)

```json
{
  "image_sha256": "sha256:<hash>",
  "verdict": "NON_COMPLIANT",
  "triggered_rules": ["R-03"],
  "detections": {
    "c2pa": "FOUND",
    "exif": "NOT_FOUND",
    "ocr": "NOT_FOUND",
    "watermark": "UNKNOWN"
  },
  "robustness": {
    "jpeg_q50": 0.0,
    "instagram_sim": 0.0
  },
  "recommendation": "비가시 워터마크가 발견됐으나 사람 인식 안내 텍스트가 없습니다.",
  "timestamp": "2026-09-07T00:00:00Z"
}
```

---

## 디렉터리 구조 / Directory Structure

```
koai_verify/
  __init__.py          # 공개 API: verify(), Verdict, DetectionResult
  api.py               # 고수준 verify() 함수
  cli.py               # Click CLI (koai-verify <image>)
  pipeline.py          # 이미지 입력 파이프라인
  detectors/
    base.py            # DetectorBase 추상 클래스
    result.py          # DetectionResult(FOUND/NOT_FOUND/UNKNOWN)
    c2pa_detector.py   # C2PA 탐지
    exif_detector.py   # EXIF AI 플래그 탐지
    ocr_detector.py    # OCR 가시 라벨 탐지
    watermark_detector.py  # 오픈 워터마크 (UNKNOWN 전용)
  rules/
    engine.py          # RuleEngine + aggregate_detections()
    models.py          # Verdict 열거형
  robustness/
    harness.py         # RobustnessHarness + SurvivalReport
    transforms.py      # 변형 배터리 구현
  report/
    formatter.py       # VerificationReport + to_json/to_summary
  analysis/
    tool_fingerprint.py    # 도구별 탐지 카탈로그 (9종)
    batch_runner.py        # Phase 0 배치 분석기
    transform_survivability.py  # 변형 생존 케이스

sdk/                   # JS/TS 래퍼 (@koai/verify)
playground/            # Gradio 웹 플레이그라운드
docs/
  examples/            # 언어별 사용 예제
  rules/               # 룰 엔진 명세 (rule_engine_spec_v0.md)
  references/          # 법령·가이드라인 원문
benchmarks/            # 강건성 벤치마크 프로토콜 + 매트릭스
tests/unit/            # 868개 단위 테스트
```

---

## 판정 결과 / Verdict Definitions

| 판정 | 의미 | 주요 트리거 |
|---|---|---|
| `COMPLIANT` | 표시 요건 충족 | R-04 (가시 라벨 존재) |
| `NON_COMPLIANT` | 표시 요건 불충족 | R-03 (비가시만 존재), R-05 (표시 없음), R-07 (딥페이크) |
| `WARNING` | 경고 — 강건성 낮음 | R-06 (생존율 < 50%) |
| `UNKNOWN` | 탐지 불가 | 모든 탐지기 UNKNOWN |

---

## 관련 문서 / Related Docs

- [PRD.md](../PRD.md) — 제품 요건 정의
- [룰 엔진 명세](rules/rule_engine_spec_v0.md) — R-01~R-07 원문 기반 판정 규칙
- [갭 리포트 v1](gap_report_v1.md) — 9개 도구 실측 결과
- [강건성 벤치마크 프로토콜](../benchmarks/protocol_v1.md) — 측정 방법론

# benchmarks/protocol_v1.md — 강건성 벤치마크 측정 프로토콜 v1

> W3 산출물 | 작성일: 2026-06-07 | 담당: seokwoo han
> 기반: PLAN.md W3, PRD §3.2, rule_engine_spec_v0.md R-06
> 구현 코드: [transform_spec.py](transform_spec.py) · [matrix.py](matrix.py)

---

## 1. 목적

AI 생성 이미지의 표시 마킹(C2PA·EXIF·가시라벨·오픈워터마크)이 실제 유통 경로에서
얼마나 살아남는지 **정량적 생존율**을 측정한다.

측정 결과는:
- **R-06 룰** (생존율 < 80% → WARNING) 의 임계치 근거가 된다.
- W16 공개 강건성 벤치마크 리포트의 핵심 데이터가 된다.
- 마커(W27~) 설계 시 "어떤 변형에서 살아남는 마킹을 만들어야 하나"를 알려준다.

---

## 2. 변형 배터리 (Transform Battery)

코드: `benchmarks/transform_spec.py` — `TRANSFORM_BATTERY` (총 20개)

### 2.1 JPEG 압축 (5단계)

| 레이블 | quality | 사용 시나리오 |
|---|---|---|
| `jpeg_compress_q95` | 95 | 거의 무손실 저장 |
| `jpeg_compress_q80` | 80 | Instagram·일반 웹 기본값 |
| `jpeg_compress_q60` | 60 | 이메일 첨부·경량화 |
| `jpeg_compress_q40` | 40 | 강한 압축 |
| `jpeg_compress_q20` | 20 | 극단적 압축 |

### 2.2 WebP 변환 (3단계)

| 레이블 | quality | 사용 시나리오 |
|---|---|---|
| `webp_convert_q90` | 90 | 고품질 WebP |
| `webp_convert_q70` | 70 | Twitter 내부 포맷 |
| `webp_convert_q50` | 50 | 저대역폭 환경 |

### 2.3 리사이즈 (3단계)

| 레이블 | 배율 | 픽셀 예 (1080×1080 기준) | 알고리즘 |
|---|---|---|---|
| `resize_75pct` | 75% | 810×810 | LANCZOS |
| `resize_50pct` | 50% | 540×540 | LANCZOS |
| `resize_25pct` | 25% | 270×270 | LANCZOS |

### 2.4 크롭 (3개)

| 레이블 | 크롭 방식 | 비율 |
|---|---|---|
| `crop_center_90pct` | 중앙 크롭 | 90% |
| `crop_center_70pct` | 중앙 크롭 | 70% |
| `crop_random_80pct` | 랜덤 크롭 (seed=42) | 80% |

### 2.5 SNS 재인코딩 시뮬 (4개)

| 레이블 | 플랫폼 | 최대 px | 포맷 | 품질 | 메타 제거 |
|---|---|---|---|---|---|
| `sns_instagram` | Instagram | 1080 | JPEG | 80 | EXIF/C2PA/XMP |
| `sns_twitter` | Twitter/X | 1200 | JPEG | 78 | EXIF/C2PA/XMP |
| `sns_kakaotalk_chat` | KakaoTalk 채팅 | 1000 | JPEG | 70 | EXIF/C2PA |
| `sns_kakaotalk_profile` | KakaoTalk 프로필 | 480×480 (정방형) | JPEG | 70 | EXIF/C2PA |

> **실측 파라미터 근거**: `SNS_PARAMS` 딕셔너리 ([transform_spec.py](transform_spec.py)) 참조.
> W4 한국 도구 샘플 수집 후 갱신 예정.

### 2.6 스크린샷 시뮬 (2개)

| 레이블 | DPI | 방법 |
|---|---|---|
| `screenshot_96dpi` | 96 | RGB 재복사 + JPEG q=90 (메타 완전 소거) |
| `screenshot_72dpi` | 72 | RGB 재복사 + JPEG q=90 |

---

## 3. 측정 대상 (Detection Formats)

코드: `benchmarks/matrix.py` — `DetectionFormat`

| 포맷 | 탐지 방법 | 구현 주차 | 룰 연계 |
|---|---|---|---|
| `c2pa` | c2pa-python Reader | W6 | R-01 |
| `exif` | piexif + Pillow | W6 | R-02 |
| `visible_label` | OCR (easyocr) + 정규식 | W7 | R-04 |
| `open_watermark` | Stable Signature 등 | W7 | 참고용 |

---

## 4. 매트릭스 구조

```
행(Format) × 열(Transform) → 생존율(0.0–1.0)

          | jpeg_q95 | jpeg_q80 | ... | sns_instagram | screenshot_96dpi |
----------|----------|----------|-----|---------------|------------------|
c2pa      |   ?      |   ?      | ... |      ?        |        ?         |
exif      |   ?      |   ?      | ... |      ?        |        ?         |
visible_l |   ?      |   ?      | ... |      ?        |        ?         |
open_wm   |   ?      |   ?      | ... |      ?        |        ?         |
```

- `?` = 미측정 (`None`)
- 실제 측정: W9 강건성 하니스 (`koai_verify/robustness/harness.py`)
- 총 셀 수: 4 포맷 × 20 변형 = **80셀**

---

## 5. 측정 절차

### 5.1 샘플 요건

- 각 포맷당 최소 **10장** 테스트 이미지 필요
- 각 이미지에는 해당 마킹이 실제로 존재해야 함
- 저작권 클리어한 이미지만 사용 (`tests/fixtures/samples/`)

| 포맷 | 샘플 소스 (W4 수집 예정) |
|---|---|
| C2PA | Adobe Firefly 출력, c2pa-python으로 생성한 테스트 이미지 |
| EXIF | Stable Diffusion AUTOMATIC1111 출력 |
| 가시 라벨 | "AI 생성" 텍스트를 직접 임베드한 테스트 이미지 |
| 오픈 워터마크 | Stable Signature 인코더로 생성 (W7 이후) |

### 5.2 측정 단계

```
for each format in [C2PA, EXIF, Visible Label, Open Watermark]:
    for each sample in samples[format]:                     # ≥10장
        original_detected = detect(format, sample)          # True/False
        if not original_detected:
            skip  # 원본에서 탐지 안 되면 제외
        for each transform in TRANSFORM_BATTERY:            # 20개
            transformed = apply_transform(sample, transform)
            survived = detect(format, transformed)
            record(format, transform, survived)
    
    survival_rate[format][transform] = sum(survived) / n_samples
```

### 5.3 검출 함수 명세 (W6/W7 구현 예정)

```python
# koai_verify/detectors/base.py (W5)
def detect(fmt: DetectionFormat, image_bytes: bytes) -> bool:
    """해당 포맷의 마킹이 image_bytes 에서 탐지되면 True."""
    ...
```

---

## 6. R-06 임계치 및 경고 판정

```python
ROBUSTNESS_THRESHOLD = 0.8  # 80%

def evaluate_robustness(matrix: SurvivalMatrix) -> dict:
    failing = [c for c in matrix.cells if c.is_measured() and c.survival_rate < 0.8]
    return {"r06_triggered": len(failing) > 0, ...}
```

| 생존율 | 판정 |
|---|---|
| ≥ 80% | 강건 — 문제 없음 |
| 50–79% | R-06 WARNING — 개선 권고 |
| < 50% | R-06 WARNING — 강력 개선 권고 |
| 0% (SNS 유실) | R-06 WARNING — 보조 표시 병행 권고 |

---

## 7. 예상 결과 (가설)

W3 설계 단계에서의 예상값. W9 실측 후 업데이트.

| 포맷 | JPEG q80 | 리사이즈 50% | SNS Instagram | 스크린샷 |
|---|---|---|---|---|
| C2PA | **0–5%** | **0%** | **0%** | **0%** |
| EXIF | 95%+ | 80%+ | **0%** | **0%** |
| 가시 라벨 | 90%+ | 85%+ | 85%+ | 75%+ |
| 오픈 워터마크 (Tree-Ring) | 85%+ | 70%+ | **0%** | **0%** |

**핵심 발견 가설**: C2PA는 SNS/스크린샷에서 완전 유실 → 비가시 마킹만으로는 R-03 불충족 위험.

---

## 8. 출력 포맷

### 8.1 JSON 생존율 매트릭스

```json
{
  "cells": [
    {"format": "c2pa", "transform_label": "sns_instagram", "survival_rate": 0.0},
    {"format": "exif", "transform_label": "jpeg_compress_q80", "survival_rate": 0.95},
    ...
  ]
}
```

### 8.2 사람 읽기용 요약 (예시)

```
KoAI-Verify 강건성 벤치마크 결과 (v1)
=======================================
C2PA 매니페스트
  SNS Instagram    : ████░░░░░░  0%  ← R-06 WARNING
  JPEG q80         : ░░░░░░░░░░  3%  ← R-06 WARNING
  가시 라벨
  JPEG q80         : █████████░ 92%  ← 강건
  SNS Instagram    : ████████░░ 83%  ← 강건
```

---

## 9. 갱신 계획

| 주차 | 갱신 내용 |
|---|---|
| W4 | 한국 도구 샘플 수집 후 SNS_PARAMS 실측값 갱신 |
| W9 | 강건성 하니스로 실제 생존율 측정 — 매트릭스 채움 |
| W16 | 최종 벤치마크 결과 공개 (Tistory·GitHub·GeekNews) |
| W25 | 표준 변경 자동 모니터링 후 임계치 재검토 |

---

## 부록: 코드 빠른 참조

```python
from benchmarks.transform_spec import TRANSFORM_BATTERY, apply_transform, TransformSpec, TransformType
from benchmarks.matrix import DetectionFormat, SurvivalMatrix, empty_matrix, evaluate_robustness

# 빈 매트릭스 초기화
m = empty_matrix()

# 변형 적용
with open("sample.jpg", "rb") as f:
    src = f.read()
out = apply_transform(src, TransformSpec(type=TransformType.SNS_INSTAGRAM))

# 생존율 기록
m.set_rate(DetectionFormat.C2PA, "sns_instagram", 0.0)

# R-06 판정
result = evaluate_robustness(m)
print(result["r06_triggered"])  # True → WARNING

# JSON 내보내기
print(m.to_json())
```

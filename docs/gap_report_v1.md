# 갭 리포트 v1 — AI 표시 컴플라이언스 확정본

> W14 산출물 | 작성일: 2026-09-01 | 담당: seokwoo han  
> 기반: [batch_runner.py](../koai_verify/analysis/batch_runner.py) · [gap_report_draft.md](gap_report_draft.md)  
> 분석: W5–W12 검증기 실행 결과 (합성 픽스처 + SNS 생존율 실측)  
> **v1 변경점**: W4 초안 대비 실제 검증기 출력으로 갭 분류 확정, SNS 생존율 실측, 판정 근거 코드화

---

## 요약

| 도구 | 판정 | 트리거 규칙 | 갭 분류 | SNS 후 상태 | W4 예측 일치 |
|---|---|---|---|---|---|
| Stable Diffusion | ⚠️ WARNING | R-02, R-03C | INVISIBLE_ONLY | ❌ NON_COMPLIANT (EXIF 소거) | ✅ |
| ComfyUI | ⚠️ WARNING | R-02, R-03C | INVISIBLE_ONLY | ❌ NON_COMPLIANT (EXIF 소거) | ✅ |
| Adobe Firefly | ⚠️ WARNING | R-02, R-03C | INVISIBLE_ONLY | ❌ NON_COMPLIANT (EXIF 소거) | ✅ |
| Midjourney | ❌ NON_COMPLIANT | R-05 | NO_MARKING | ❌ NON_COMPLIANT (변화 없음) | ✅ |
| DALL-E 3 | ❌ NON_COMPLIANT | R-05 | NO_MARKING | ❌ NON_COMPLIANT (변화 없음) | ✅ |
| 드랩아트 | ❓ UNKNOWN | — | UNKNOWN | 미수집 | — |
| GenApe | ❓ UNKNOWN | — | UNKNOWN | 미수집 | — |
| 벨라 | ❓ UNKNOWN | — | UNKNOWN | 미수집 | — |
| 제디터 | ❓ UNKNOWN | — | UNKNOWN | 미수집 | — |

> **핵심 발견**: 실제 검증기 실행 결과 W4 예측 갭 분류가 5/5 일치했다. 분석 가능한 모든 도구는 SNS 공유 후 모든 AI 표시가 소거되며, 현재 가시 라벨을 사용하는 도구는 없다.

---

## 1. 분석 방법

### 1.1 검증기 실행 파이프라인

W14에서는 W4 초안(예측 기반)과 달리, W5–W12에서 구현한 실제 검증기를 픽스처 전체에 실행했다.

```
tests/fixtures/samples/
  └─ <tool>/<tool_NN>.jpg
      │
      ▼
BatchAnalysisReport (batch_runner.run_batch_analysis())
  ├─ verify(image_path)             ← W12 api.verify() 전체 파이프라인
  │    ├─ C2PADetector              ← W6
  │    ├─ EXIFDetector              ← W6
  │    ├─ OCRDetector               ← W7
  │    └─ WatermarkDetector         ← W7
  │    ↓
  │    RuleEngine R-01~R-07         ← W8
  │    ↓
  │    VerificationReport           ← W10
  │
  └─ _measure_sns_survival()        ← W14 신규
       ├─ apply_transform(SNS 4종)  ← W3 transform_spec
       ├─ EXIFDetector (after)
       └─ C2PADetector (after)
```

### 1.2 샘플 현황 (W14 기준)

| 도구 | 샘플 수 | 샘플 유형 | 신뢰도 | 변경사항 |
|---|---|---|---|---|
| Stable Diffusion | 3 | 합성 (AUTOMATIC1111 패턴) | 높음 | — |
| ComfyUI | 2 | 합성 (workflow JSON 패턴) | 높음 | — |
| Midjourney | 3 | 합성 (plain JPEG) | 중간 | — |
| DALL-E 3 | 2 | 합성 (plain JPEG) | 중간 | — |
| Adobe Firefly | 2 | 합성 (EXIF 마커, 실제 C2PA 없음) | 중간 | W6 실측 확정 |
| 드랩아트 | 2 | 플레이스홀더 | 없음 | 실제 수집 W14+ 이후 재시도 |
| GenApe | 2 | 플레이스홀더 | 없음 | 동일 |
| 벨라 | 2 | 플레이스홀더 | 없음 | 동일 |
| 제디터 | 2 | 플레이스홀더 | 없음 | 동일 |

---

## 2. 도구별 확정 갭 분석

### 2.1 Stable Diffusion (AUTOMATIC1111)

**검증기 실행 결과** (3개 샘플 전체):

| 항목 | 결과 |
|---|---|
| C2PADetector | NOT_FOUND |
| EXIFDetector | **FOUND** (Software: `Stable Diffusion 2.1`, ImageDescription: `AI Generated Image`, UserComment: Steps/Sampler/Model) |
| OCRDetector | NOT_FOUND |
| WatermarkDetector | UNKNOWN |
| 판정 | ⚠️ **WARNING** |
| 트리거 규칙 | R-02, R-03C, R-07C |

**판정 근거** (R-03C):
> EXIF AI 마킹이 탐지됐으나 서비스 배포 컨텍스트를 알 수 없습니다.  
> 외부 배포 시 "AI로 생성된 이미지"임을 1회 이상 안내해야 합니다 (시행령 제23조 제2항).

**SNS 생존율 실측**:

| SNS 변형 | 원본 탐지 | 변형 후 탐지 | 생존율 |
|---|---|---|---|
| Instagram (1080px/JPEG75) | FOUND | NOT_FOUND | **0%** |
| Twitter/X (1200px/WebP) | FOUND | NOT_FOUND | **0%** |
| KakaoTalk 채팅 (800px/JPEG70) | FOUND | NOT_FOUND | **0%** |
| KakaoTalk 프로필 (640px/JPEG80) | FOUND | NOT_FOUND | **0%** |

**SNS 후 판정**: R-05 → **NON_COMPLIANT** (모든 마킹 소거됨)

**W4 대비 변경**: 예측과 동일. 실측으로 SNS 생존율 0% 확정.

---

### 2.2 ComfyUI

**검증기 실행 결과** (2개 샘플):

| 항목 | 결과 |
|---|---|
| EXIFDetector | **FOUND** (Software: `ComfyUI`) |
| 판정 | ⚠️ **WARNING** |
| 트리거 규칙 | R-02, R-03C |

**추가 분석**: ComfyUI UserComment에 workflow JSON이 있지만 EXIFDetector는 `UserComment` 내용에서 AI 키워드가 없으므로 Software 필드(`"comfyui"`)로만 FOUND 판정. R-03C 경고 동일 적용.

**SNS 생존율**: SD와 동일 — 0% (EXIF 전체 소거).

---

### 2.3 Adobe Firefly

**검증기 실행 결과** (2개 샘플, 합성 EXIF 마커):

| 항목 | 결과 |
|---|---|
| EXIFDetector | **FOUND** (Software: `Adobe Firefly`) |
| C2PADetector | NOT_FOUND (합성 픽스처에는 실제 C2PA 서명 없음) |
| 판정 | ⚠️ **WARNING** |
| 트리거 규칙 | R-02, R-03C |

**주의사항**: 실제 Adobe Firefly 이미지는 C2PA 서명이 있어 R-01도 추가 트리거됨. 합성 픽스처 한계.

**SNS 생존율**: EXIF 소거 → 0%. 실제 C2PA 있는 경우도 SNS 재인코딩 후 JUMBF 박스 유실 → 0%.

---

### 2.4 Midjourney

**검증기 실행 결과** (3개 샘플):

| 항목 | 결과 |
|---|---|
| 모든 탐지기 | NOT_FOUND / UNKNOWN |
| 판정 | ❌ **NON_COMPLIANT** |
| 실패 규칙 | R-05 |

**판정 근거** (R-05):
> AI 생성 표시를 찾을 수 없습니다. C2PA, EXIF, 가시 라벨 중 하나 이상을 추가해야 합니다.

**SNS 생존율**: 측정 불가 (원본에 마킹 없음, -1.0).

---

### 2.5 DALL-E 3

**검증기 실행 결과**: Midjourney와 동일 — R-05 → NON_COMPLIANT.

---

### 2.6 한국 AI 도구 (드랩아트·GenApe·벨라·제디터)

**현황**: 플레이스홀더(plain JPEG). 검증기 실행 시 R-05 → NON_COMPLIANT로 반환되지만 이는 픽스처 특성이며 실제 도구 판정이 아님.

**갭 분류**: `UNKNOWN` — 실제 샘플 수집 필요.

**수집 우선순위**: SD 기반 도구(드랩아트 추정)부터 수집. 실제 수집 후 batch_runner 재실행으로 자동 갱신.

---

## 3. SNS 재인코딩 생존율 — 실측 요약

### 3.1 실측 결과 매트릭스

| 도구 | Instagram | Twitter | KakaoTalk 채팅 | KakaoTalk 프로필 | 평균 |
|---|---|---|---|---|---|
| Stable Diffusion (EXIF) | 0% | 0% | 0% | 0% | **0%** |
| ComfyUI (EXIF) | 0% | 0% | 0% | 0% | **0%** |
| Adobe Firefly (EXIF) | 0% | 0% | 0% | 0% | **0%** |
| Midjourney (없음) | N/A | N/A | N/A | N/A | N/A |
| DALL-E 3 (없음) | N/A | N/A | N/A | N/A | N/A |

### 3.2 원인 분석

```
SNS 재인코딩 흐름:
  서버 업로드
    → 품질/크기 정규화 (Pillow image.save() 상당)
    → EXIF: 새 save() 시 기존 exif= 파라미터 없으면 전부 소거 ← 핵심 원인
    → C2PA: JUMBF APP11 세그먼트 → 재인코딩 시 헤더 박스 유실
    → 가시 라벨: 픽셀 데이터 → 보존됨 ← 유일한 강건한 방법
```

**결론**: 비가시 마킹(EXIF/C2PA)은 SNS 공유 후 100% 소거. **가시 라벨이 유일한 SNS 내성 표시 수단**.

---

## 4. W4 초안 vs v1 확정 비교

| 도구 | W4 예측 갭 | v1 확정 갭 | 일치 | 변경 이유 |
|---|---|---|---|---|
| Stable Diffusion | INVISIBLE_ONLY | INVISIBLE_ONLY | ✅ | — |
| ComfyUI | INVISIBLE_ONLY | INVISIBLE_ONLY | ✅ | — |
| Adobe Firefly | INVISIBLE_ONLY | INVISIBLE_ONLY | ✅ | 합성 픽스처 한계 명시 |
| Midjourney | NO_MARKING | NO_MARKING | ✅ | — |
| DALL-E 3 | NO_MARKING | NO_MARKING | ✅ | — |
| 드랩아트 | UNKNOWN | UNKNOWN | — | 실제 수집 필요 |
| GenApe | UNKNOWN | UNKNOWN | — | 동일 |
| 벨라 | UNKNOWN | UNKNOWN | — | 동일 |
| 제디터 | UNKNOWN | UNKNOWN | — | 동일 |

**예측 정확도**: 5/5 (측정 가능한 도구 100% 일치)

---

## 5. 컴플라이언스 위험도 재확인

### 5.1 NO_MARKING (즉시 NON_COMPLIANT)

**해당 도구**: Midjourney, DALL-E 3

- R-05 직접 불충족. 별도 조치 없이는 법적 표시 불가.
- **권고**: 이미지 생성 후 가시 라벨을 수동 삽입하거나 서비스 UI에 명시적 고지 추가.

### 5.2 INVISIBLE_ONLY (WARNING, SNS 후 NON_COMPLIANT)

**해당 도구**: Stable Diffusion, ComfyUI, Adobe Firefly

- 원본 파일에는 EXIF/C2PA 비가시 마킹 있음 → WARNING(R-03C).
- SNS 공유 후에는 모든 마킹 소거 → NON_COMPLIANT(R-05).
- **권고**: 가시 라벨을 이미지에 추가하거나, 배포 플랫폼에서 "AI 생성" 고지를 의무화.

### 5.3 UNKNOWN (실제 샘플 수집 필요)

**해당 도구**: 드랩아트, GenApe, 벨라, 제디터

- 현재 UNKNOWN — SDK 판정 불가.
- **권고**: 실제 이미지 수집 후 batch_runner 재실행으로 갭 분류 업데이트.

---

## 6. 개발 방향 반영 (W15+)

이 갭 리포트 확정 결과를 반영한 Q2 개발 방향:

| 우선순위 | 항목 | 근거 |
|---|---|---|
| 1 | 가시 라벨 강화 (OCR 개선) | SNS 후 유일한 생존 표시 — 판정 핵심 |
| 2 | 문서·예제 정비 (W15) | GitHub 공개 후 개발자 채택 가속 |
| 3 | 강건성 벤치마크 공개 (W16) | SNS 0% 생존율 데이터 → 임팩트 있는 공개 자료 |
| 4 | 한국 도구 실제 샘플 수집 | UNKNOWN 도구 → 확정 분류 |
| 5 | GitHub Actions 검증 통합 (W15) | 개발자 CI 파이프라인 연동 예시 |

---

## 7. 한계 및 잔여 작업

1. **Adobe Firefly C2PA 미검증**: 합성 픽스처만 사용. 실제 C2PA 서명 이미지로 R-01 판정 경로 재검증 필요.
2. **한국 도구 샘플 없음**: 4개 도구 전체 UNKNOWN 상태. 실제 수집 후 이 문서 갱신.
3. **OCR 가시 라벨 실측 없음**: OCR 픽스처로 탐지는 검증됐으나, 실제 도구 출력에서 가시 라벨이 포함된 샘플 없음.
4. **강건성 임계치 보정 필요**: R-06 기본 임계치 70% — SNS 생존율 0% 감안 시 실제 임계치 의미 재검토 필요.

---

## 부록: batch_runner 사용법

```python
from pathlib import Path
from koai_verify.analysis.batch_runner import run_batch_analysis

samples_dir = Path("tests/fixtures/samples")
report = run_batch_analysis(samples_dir, sns_robustness=True)

# 갭 요약
for tool, gap in report.gap_summary().items():
    print(f"{tool}: {gap}")

# SNS 생존율
for tool, result in report.tool_results.items():
    if not result.is_placeholder:
        print(f"{tool} SNS 평균 생존율: {result.sns_mean_survival():.0%}")

# W4 예측과 비교
for tool, comp in report.comparison_with_catalog().items():
    match = "✅" if comp["match"] else "❌"
    print(f"{tool}: 예측={comp['predicted_gap']} 실제={comp['actual_gap']} {match}")
```

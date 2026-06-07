# gap_report_draft.md — AI 표시 컴플라이언스 갭 리포트 초안

> W4 산출물 | 작성일: 2026-06-07 | 담당: seokwoo han
> 기반 모듈: [koai_verify/analysis/tool_fingerprint.py](../koai_verify/analysis/tool_fingerprint.py)
>           [koai_verify/analysis/transform_survivability.py](../koai_verify/analysis/transform_survivability.py)
> 분석 샘플: [tests/fixtures/samples/](../tests/fixtures/samples/) (합성 픽스처, 한국 도구는 플레이스홀더)

---

## 요약

| 도구 | C2PA | EXIF AI | 가시 라벨 | 갭 분류 | R-03 위험 | SNS 후 상태 |
|---|---|---|---|---|---|---|
| Stable Diffusion | ❌ | ✅ | ❌ | INVISIBLE_ONLY | ⚠️ 있음 | ❌ EXIF 소거 → NO_MARKING |
| ComfyUI | ❌ | ✅ | ❌ | INVISIBLE_ONLY | ⚠️ 있음 | ❌ EXIF 소거 → NO_MARKING |
| Adobe Firefly | ✅ | ❌ | ❌ | INVISIBLE_ONLY | ⚠️ 있음 | ❌ C2PA 소거 → NO_MARKING |
| Midjourney | ❌ | ❌ | ❌ | NO_MARKING | — | NO_MARKING (변화 없음) |
| DALL-E 3 | ❌ | ❌ | ❌ | NO_MARKING | — | NO_MARKING (변화 없음) |
| 드랩아트 | ❓ | ❓ | ❓ | UNKNOWN | ❓ | 미수집 |
| GenApe | ❓ | ❓ | ❓ | UNKNOWN | ❓ | 미수집 |
| 벨라 | ❓ | ❓ | ❓ | UNKNOWN | ❓ | 미수집 |
| 제디터 | ❓ | ❓ | ❓ | UNKNOWN | ❓ | 미수집 |

**핵심 발견**: 분석 가능한 5개 도구 중 어떤 도구도 SNS 공유 후 AI 표시를 유지하지 못한다. 가시 라벨을 사용하는 도구는 현재 없다.

---

## 1. 분석 방법

### 1.1 분석 파이프라인

```
합성 픽스처 (tests/fixtures/samples/)
  → ToolFingerprint 분석 (koai_verify/analysis/tool_fingerprint.py)
      C2PA: c2pa-python Reader
      EXIF: piexif UserComment / Software / ImageDescription
      가시 라벨: W7 이전 → NOT_FOUND 고정
  → W3 변형 배터리 적용 (benchmarks/transform_spec.py)
  → 변형 후 재분석 → SurvivalOutcome 분류
  → GapCategory 판정 (R-01~R-05 기반)
```

### 1.2 샘플 현황

| 도구 | 샘플 수 | 샘플 유형 | 신뢰도 |
|---|---|---|---|
| Stable Diffusion | 3 | 합성 (AUTOMATIC1111 패턴 재현) | 높음 |
| ComfyUI | 2 | 합성 (workflow JSON 패턴 재현) | 높음 |
| Midjourney | 3 | 합성 (메타데이터 없는 plain JPEG) | 중간 |
| DALL-E 3 | 2 | 합성 (plain JPEG) | 중간 |
| Adobe Firefly | 2 | 합성 (EXIF 마커, 실제 C2PA 없음) | 낮음 — W6 검증 필요 |
| 드랩아트 | 1 | 플레이스홀더 | 없음 — 실제 수집 필요 |
| GenApe | 1 | 플레이스홀더 | 없음 — 실제 수집 필요 |
| 벨라 | 1 | 플레이스홀더 | 없음 — 실제 수집 필요 |
| 제디터 | 1 | 플레이스홀더 | 없음 — 실제 수집 필요 |

---

## 2. 도구별 갭 분석

### 2.1 Stable Diffusion (AUTOMATIC1111)

**탐지 결과**:
- EXIF Software: `Stable Diffusion 2.1` — **FOUND**
- EXIF UserComment: SD 생성 파라미터 (Steps, Sampler, Model...) — **FOUND**
- C2PA: 없음 — **NOT_FOUND**
- 가시 라벨: W7 미구현 — **NOT_FOUND**

**갭 분류**: `INVISIBLE_ONLY`

**컴플라이언스 분석**:
- R-01(C2PA): 불충족
- R-02(EXIF): 충족 후보 (EXIF 있음)
- R-03(비가시+안내): **핵심 위험** — EXIF만 있고 "사람 인식 안내" 없으면 R-03 불충족
- R-04(가시 라벨): 탐지 불가
- R-05(어떤 표시도 없음): EXIF 있으므로 일단 해당 없음

**변형 후 결과**:

| 변형 | EXIF 생존 | SNS 후 갭 분류 |
|---|---|---|
| JPEG q80 (직접 압축) | ✅ FOUND | INVISIBLE_ONLY 유지 |
| JPEG q20 (심한 압축) | ✅ FOUND | INVISIBLE_ONLY 유지 |
| 리사이즈 50% | ✅ FOUND | INVISIBLE_ONLY 유지 |
| Instagram 업로드 시뮬 | ❌ NOT_FOUND | **NO_MARKING → R-05** |
| Twitter 업로드 시뮬 | ❌ NOT_FOUND | **NO_MARKING → R-05** |
| KakaoTalk 전송 시뮬 | ❌ NOT_FOUND | **NO_MARKING → R-05** |
| 스크린샷 (96 DPI) | ❌ NOT_FOUND | **NO_MARKING → R-05** |

**결론**: SD 출력 이미지는 직접 파일로 공유하면 EXIF가 남지만, SNS를 거치면 모든 표시가 소거된다. 한국 AI 기본법 준수를 위해 가시 라벨 추가가 필수적이다.

---

### 2.2 ComfyUI

**탐지 결과**:
- EXIF Software: `ComfyUI` — **FOUND**
- EXIF UserComment: workflow JSON (`{"nodes": [...]}`) — **FOUND**
- C2PA: 없음 — **NOT_FOUND**
- 가시 라벨: W7 미구현 — **NOT_FOUND**

**갭 분류**: `INVISIBLE_ONLY`

**컴플라이언스 분석**:
- R-02(EXIF): 충족 후보
- R-03: **위험** — SD와 동일한 구조, 안내 없으면 불충족
- SNS 공유 후: EXIF 소거 → `NO_MARKING`

**SD와의 차이점**: ComfyUI는 workflow JSON을 UserComment에 직접 삽입 — 기계 판독은 용이하나 사람 인식에는 부적합. R-03 충족을 위한 "사람 읽기 가능 안내"가 별도 필요하다.

---

### 2.3 Adobe Firefly

**탐지 결과** (합성 픽스처 기준):
- EXIF Software: `Adobe Firefly` (합성 마커) — **FOUND** (단, 실제 C2PA 없음)
- C2PA: 실제 이미지에서는 **FOUND** — W6에서 실제 서명 검증 필요
- 가시 라벨: **NOT_FOUND**

**갭 분류**: `INVISIBLE_ONLY` (C2PA 있어도 비가시 마킹만 있음)

**컴플라이언스 분석**:
- R-01(C2PA): 충족 후보 (실제 이미지 검증 필요)
- R-03: **여전히 위험** — C2PA가 있어도 사람이 인식하지 못하면 안내 없이는 불충족

**변형 후 결과** (공개 문서 기반 추정):

| 변형 | C2PA 생존 |
|---|---|
| 원본 파일 그대로 | ✅ |
| JPEG q80 재압축 | ❌ JUMBF 박스 유실 |
| WebP 변환 | ❌ |
| Instagram 업로드 | ❌ |
| 스크린샷 | ❌ |

**추정 SNS 후 생존율**: 0% (C2PA는 SNS 재인코딩에서 완전 소거)

**결론**: Firefly는 C2PA로 원본 파일에서는 최선의 마킹을 제공하지만, SNS 공유 시나리오에서는 모든 표시가 사라진다. 이는 Firefly 도구의 문제가 아니라, 비가시 마킹 방식의 구조적 한계다.

---

### 2.4 Midjourney

**탐지 결과**:
- C2PA: **NOT_FOUND**
- EXIF AI 마킹: **NOT_FOUND**
- 가시 라벨: **NOT_FOUND**

**갭 분류**: `NO_MARKING`

**컴플라이언스 분석**:
- R-05 직접 불충족 — 어떤 마킹도 없음
- SNS 공유 후: 변화 없음 (원래부터 마킹 없음)

**R-03 위험 여부**: 해당 없음 — R-03은 비가시 마킹이 있을 때 가시 안내 요건. Midjourney는 R-05(어떤 표시도 없음) 직접 해당.

---

### 2.5 DALL-E 3

**탐지 결과**:
- C2PA: **NOT_FOUND** (2026년 기준 미지원)
- EXIF AI 마킹: **NOT_FOUND**
- 가시 라벨: **NOT_FOUND**

**갭 분류**: `NO_MARKING`

**컴플라이언스 분석**: Midjourney와 동일 — R-05 직접 불충족.

---

### 2.6 한국 AI 도구 (드랩아트·GenApe·벨라·제디터)

**현황**: W4 실제 샘플 수집 미완료. 플레이스홀더(plain JPEG) 상태.

**갭 분류**: `UNKNOWN` — 실제 출력 이미지 분석 전까지 판정 불가.

**수집 방법론**:
1. 각 도구에서 동일한 프롬프트로 이미지 생성
2. 다운로드 직후 픽스처 저장 (SNS 경유 없이)
3. `fingerprint_image()` 실행
4. 결과를 이 문서에 갱신

**합리적 가설** (SD 기반 가능성 있음):
- 드랩아트: SD 기반 가능성 → EXIF 있을 수 있음
- GenApe: 미상
- 벨라: 미상
- 제디터: 영상·이미지 편집 도구, AI 생성 기능 여부 미확인

---

## 3. 변형 후 마킹 소거 케이스 목록

W4 분석에서 확인된 주요 마킹 소거 시나리오:

### 3.1 SNS 재인코딩에 의한 소거

| 도구 | 마킹 타입 | 변형 | 결과 |
|---|---|---|---|
| Stable Diffusion | EXIF AI | Instagram 업로드 | ❌ NOT_FOUND |
| Stable Diffusion | EXIF AI | Twitter 업로드 | ❌ NOT_FOUND |
| Stable Diffusion | EXIF AI | KakaoTalk 전송 | ❌ NOT_FOUND |
| Adobe Firefly | C2PA | Instagram 업로드 | ❌ NOT_FOUND (추정) |
| Adobe Firefly | C2PA | JPEG 재압축 | ❌ NOT_FOUND (추정) |

**원인**: SNS 플랫폼은 서버 측에서 이미지를 재인코딩한다. JPEG 재인코딩 시:
- EXIF: Pillow 기본 save() 는 보존하지 않음
- C2PA: JUMBF 박스가 JPEG 헤더에 별도 삽입 → 재인코딩 시 유실
- 가시 라벨: 픽셀 데이터에 포함 → **보존됨** (SNS 후에도 생존)

### 3.2 스크린샷에 의한 소거

| 마킹 | 스크린샷 후 | 설명 |
|---|---|---|
| EXIF | ❌ 소거 | 픽셀만 캡처, 메타데이터 미포함 |
| C2PA | ❌ 소거 | 동일 |
| 가시 라벨 | ✅ 보존 | 픽셀에 텍스트 포함됨 |

---

## 4. GapCategory별 컴플라이언스 위험도

### 4.1 NO_MARKING (가장 위험)

해당 도구: **Midjourney, DALL-E 3**

- R-05 직접 불충족
- 별도 가시 라벨 없이는 완전한 법적 불충족
- SDK 판정: `NON_COMPLIANT` (R-05 트리거)

### 4.2 INVISIBLE_ONLY (조건부 위험)

해당 도구: **Stable Diffusion, ComfyUI, Adobe Firefly**

- R-03 핵심 위험 — 비가시 마킹만으로는 불충족
- **"1회 이상 안내"가 있으면 충족 가능** (법령 §31조 ②)
- SDK 판정: `WARNING` (R-03 pending)
- SNS 공유 후: 비가시 소거 → `NON_COMPLIANT`

### 4.3 DETECTABLE (충족 가능)

현재 해당 도구: **없음** (가시 라벨 채택 도구 미발견)

- R-04 충족 → 이미지 자체에 표시
- SNS 후에도 생존 가능

### 4.4 UNKNOWN

해당 도구: **드랩아트, GenApe, 벨라, 제디터**

- 실제 샘플 수집 전까지 판정 불가
- SDK 판정: `UNKNOWN`

---

## 5. 룰 엔진 R-03 상세 분석

R-03은 이 프로젝트에서 가장 중요한 판정 규칙이다.

> **R-03**: 비가시 마킹(C2PA/EXIF/워터마크)만 있고 "사람이 인식할 수 있는 안내"가 없으면 → 법적 불충족

```
비가시 마킹 FOUND
  + 가시 라벨 NOT_FOUND
  + 플랫폼 고지 확인 불가
  → R-03: WARNING / NON_COMPLIANT (컨텍스트 의존)
```

**실무 함의**:
- Stable Diffusion, ComfyUI로 생성한 이미지를 SNS에 게시할 때 별도 텍스트 없이 올리면 불충족
- Adobe Firefly C2PA도 사람이 직접 인식하지 못하면 동일
- **가시 라벨이 유일한 강건한 법적 준수 수단**

---

## 6. W5+ 개발 우선순위 반영

이 갭 리포트를 기반으로 개발 우선순위를 다음과 같이 권장한다:

| 우선순위 | 항목 | 근거 |
|---|---|---|
| 1 | EXIF 탐지 엔진 (W6) | SD/ComfyUI 커버, 국내 개발자 채택 비율 높음 |
| 2 | C2PA 탐지 엔진 (W6) | Firefly·Adobe 생태계, 표준 방향성 |
| 3 | OCR 가시 라벨 탐지 (W7) | SNS 후 유일한 생존 마킹, R-03 판정 핵심 |
| 4 | R-03 컨텍스트 판정 로직 (W8) | 비가시+안내 여부 조합 판정 |
| 5 | 강건성 하니스 (W9) | R-06 생존율 실측 |

---

## 7. 한계 및 다음 단계

### 7.1 현재 한계

1. **한국 도구 샘플 없음**: 드랩아트·GenApe·벨라·제디터 실제 출력 미확보. 플레이스홀더로 구조만 검증.
2. **Adobe Firefly C2PA 미검증**: 실제 C2PA 서명된 이미지 없음. 합성 픽스처로 구조만 검증. W6에서 실제 서명 검증 필요.
3. **OCR 가시 라벨 미구현**: W7 이전까지 NOT_FOUND 고정. 실제 라벨 있는 이미지 판정 불가.
4. **오픈 워터마크 미탐지**: W7 이전까지 UNKNOWN 고정.

### 7.2 다음 단계

- **W5**: 레포 CI 구성, 코어 패키지 초기화
- **W6**: C2PA + EXIF 탐지 엔진 구현, 실제 Firefly 이미지 검증
- **W7**: OCR 가시 라벨 + Stable Signature 탐지
- **W8 전**: 한국 AI 도구 실제 샘플 수집 재시도 → UNKNOWN → 확정 분류

---

## 부록: GapCategory 판정 로직

```python
def _classify_gap(fp: ToolFingerprint) -> GapCategory:
    if fp.c2pa == UNKNOWN and fp.exif_ai == UNKNOWN:
        return GapCategory.UNKNOWN

    if fp.visible_label == FOUND:
        return GapCategory.DETECTABLE            # R-04 충족 가능

    if fp.c2pa == FOUND or fp.exif_ai == FOUND:
        return GapCategory.INVISIBLE_ONLY        # R-03 위험

    return GapCategory.NO_MARKING               # R-05 직접 불충족
```

**R-03이 핵심인 이유**: 비가시만 있고 안내가 없으면 일반인이 AI 생성 이미지임을 알 방법이 없다. 법령은 "사람이 인식할 수 있는" 방법을 요구한다.

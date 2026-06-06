# 룰 엔진 명세 v0 — 제31조 표시 의무 판정 규칙

> 버전: 0.2 (2026-06-06, W1 원문 확정)
> 근거 법령: 「인공지능 발전과 신뢰 기반 조성 등에 관한 기본법」 제31조 (법률 제20676호, 2026.1.22 시행)
> 근거 지침: 과기정통부 「인공지능 투명성 확보 가이드라인」 (2026.01.22 공개), 시행령 제23조
> 상태: **확정** (원문 PDF 기반, 가이드라인 전체 정독 완료)
> 연계: [PRD.md §4](../../PRD.md), [checklist_mapping.md](checklist_mapping.md), [../references/AI_투명성_확보_가이드라인_원문요약.md](../references/AI_투명성_확보_가이드라인_원문요약.md)

---

## 1. 법적 근거 (원문 기반 확정)

### 「인공지능 발전과 신뢰 기반 조성 등에 관한 기본법」 제31조 인공지능 투명성 확보 의무

| 항 | 적용 조건 | 의무 내용 |
|---|---|---|
| **제1항** | 고영향 인공지능이나 생성형 인공지능을 이용한 제품·서비스를 제공하려는 경우 | AI 기반 운용 사실을 이용자에게 **사전 고지** |
| **제2항** | 생성형 인공지능 또는 이를 이용한 제품·서비스를 제공하는 경우 | 결과물이 생성형 인공지능에 의하여 생성되었다는 사실을 **표시** |
| **제3항** | 인공지능 시스템을 이용하여 실제와 구분하기 어려운 가상의 음향·이미지·영상 등의 결과물을 제공하는 경우 | 해당 결과물이 인공지능에 의하여 생성되었다는 사실을 이용자가 명확하게 알 수 있도록 **고지 또는 표시** |

> ※ 예술적·창의적 표현물(미술·영화·문학·사진·출판·만화·게임·애니메이션 등)에 해당하는 경우 전시·향유를 저해하지 않는 방식으로 표시 가능 (제3항 단서)

### 시행령 제23조 — 고지 및 표시 방법

**제1항 — 사전고지 방법**
1. 제품 등에 직접 기재하거나, 계약서·사용설명서·이용약관 등에 기재
2. 이용자의 화면 또는 단말기 등에 표시
3. 제품 등을 제공하는 장소에 인식하기 쉬운 방법으로 게시
4. 그 밖에 제품 등의 특성을 고려하여 과학기술정보통신부장관이 인정하는 방법

**제2항 — 표시 방법 ★ 룰 엔진 핵심**
1. 표시 방법은 **사람이 인식할 수 있는 방법**과 **기계가 판독할 수 있는 방법**이 있음
2. **기계가 판독할 수 있는 방법을 사용할 경우에는 최소 1회 이상 안내 문구·음성 등을 제공해야 함**

**제3항 — 딥페이크 표시 고려사항**
1. 이용자가 시각·청각 등을 통하거나 소프트웨어 등을 이용하여 쉽게 내용을 확인할 수 있는 방법
2. 주된 이용자의 연령, 신체적·사회적 조건 등을 고려하여 고지 또는 표시

### 서비스 내 vs. 외부 반출 판정 기준

| 구분 | 표시 위치 | 허용 방법 |
|---|---|---|
| **서비스 이용 환경 내** | 결과물 내 OR 서비스 UI | 사람 인식 OR 기계 판독 + 1회 안내 |
| **외부 반출** (다운로드·공유) | **결과물 자체에 반드시 표시** | 사람 인식 OR 기계 판독 + 1회 안내 |
| **딥페이크 외부 반출** | 결과물 자체에 반드시 표시 | **사람이 인식할 수 있는 방법만** (비가시 단독 불가) |

---

## 2. 적용 범위

| 대상 | 적용 여부 | 비고 |
|---|---|---|
| AI 생성 이미지 | ✅ 적용 | 본 v0 룰셋 주 대상 |
| AI 생성 영상 | ⏳ Q4 확장 | 별도 룰셋 예정 |
| AI 생성 오디오 | ⏳ Q4 확장 | 별도 룰셋 예정 |
| AI 생성 텍스트 | 🔲 미정 | 가이드라인은 파일 메타데이터 + 1회 안내로 충족 가능 |
| AI 보조 생성(사람 편집 포함) | 🔲 미정 | 편집 중간 생성물은 의무 없음, 최종 결과물만 해당 |
| 클립보드 복사 | ❌ 제외 | 가이드라인 명시 제외 |
| 단순 편집 (AI 기능 미사용) | ❌ 제외 | 이미지 자르기 등 |

---

## 3. 데이터 모델

### 3.1 탐지 결과 (DetectionResult)

```python
class DetectionStatus(Enum):
    FOUND     = "found"      # 표시 존재 확인
    NOT_FOUND = "not_found"  # 표시 없음 확인
    UNKNOWN   = "unknown"    # 탐지 불가 (비공개 포맷 등)

@dataclass
class DetectionResult:
    detector: str              # "c2pa" | "exif" | "ocr" | "watermark"
    status: DetectionStatus
    confidence: float | None   # 0.0~1.0 (UNKNOWN이면 None)
    detail: dict               # 탐지기별 부가 정보
```

### 3.2 검증 컨텍스트 (VerificationContext)

```python
@dataclass
class VerificationContext:
    # 서비스 배포 컨텍스트 — 알 수 없으면 None
    is_external_distribution: bool | None  # True=외부반출, False=서비스내, None=불명
    download_notice_confirmed: bool | None # 다운로드 시 1회 안내 제공 여부
    is_deepfake_service: bool | None       # 딥페이크 생성 서비스 여부
    is_artistic_work: bool | None          # 예술적·창의적 표현물 여부
```

### 3.3 판정 결과 (Verdict)

```python
class Verdict(Enum):
    COMPLIANT     = "compliant"      # 제31조 충족
    NON_COMPLIANT = "non_compliant"  # 명백한 불충족
    WARNING       = "warning"        # 충족 가능성 있으나 컨텍스트 불명
    UNKNOWN       = "unknown"        # 판정 불가 (탐지 결과 부족)

@dataclass
class RuleVerdict:
    verdict: Verdict
    triggered_rules: list[str]   # 판정에 기여한 규칙 ID 목록
    failing_rules: list[str]     # 불충족을 유발한 규칙 ID 목록
    recommendation: str          # 사람이 읽는 조치 권고문
```

---

## 4. 룰셋 정의

### R-01: C2PA 매니페스트 유효성

```
조건: detectors["c2pa"].status == FOUND
      AND c2pa_manifest.is_valid_signature == True
      AND c2pa_manifest.has_ai_assertion == True
분류: 기계 판독 방식 (비가시)
결과: 비가시_충족_후보
근거: 시행령 제23조 제2항 — 기계가 판독할 수 있는 방법
비고: 서명 유효성 검증 필수 — 서명 없는 매니페스트는 위변조 가능
     has_ai_assertion: c2pa.actions 또는 c2pa.ai.generatedContent assertion 존재
```

### R-02: EXIF/XMP AI 플래그

```
조건: detectors["exif"].status == FOUND
      AND exif.has_ai_flag == True  (아래 필드 중 하나 이상)
분류: 기계 판독 방식 (비가시)
결과: 비가시_충족_후보
근거: 시행령 제23조 제2항 — 메타데이터를 활용한 비가시적 방법

확인 필드 목록 (v0, W2에서 확정):
  - XMP: Iptc4xmpExt:DigitalSourceType =
         "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
  - XMP: dc:rights (AI 생성 문구 포함 여부)
  - EXIF: UserComment (파싱 후 AI 관련 키워드)
  - EXIF: Software (AI 생성 도구명 패턴 — 보조 지표만)
```

### R-03: 비가시 전용 + 1회 안내 확인 ★ 핵심 규칙 (v0.2 수정)

```
[원문 근거] 시행령 제23조 제2항:
  "기계가 판독할 수 있는 방법을 사용할 경우에는 최소 1회 이상 안내 문구·음성 등을 제공해야 함"

조건: (R-01 OR R-02) == 비가시_충족_후보   # 비가시 마크 존재
      AND R-04 미발동                       # 가시 라벨 없음

케이스 A — 1회 안내 확인됨:
  조건: context.download_notice_confirmed == True
  결과: COMPLIANT
  근거: 시행령 요건 충족

케이스 B — 1회 안내 없음이 확인됨:
  조건: context.download_notice_confirmed == False
        AND context.is_external_distribution == True
  결과: NON_COMPLIANT
  권고: "비가시 표시(워터마크·메타데이터)만 탐지됐으나 외부 배포 시 필수인
        다운로드 안내 문구가 없습니다. 다운로드 시 'AI로 생성된 이미지입니다'
        등의 안내를 1회 이상 제공하세요."

케이스 C — 컨텍스트 불명 (이미지 단독 검증):
  조건: context.download_notice_confirmed == None
  결과: WARNING
  권고: "비가시 표시만 탐지됐습니다. 이미지를 외부로 배포하는 경우
        다운로드 시 AI 생성 사실을 1회 이상 안내해야 합니다
        (시행령 제23조 제2항). 서비스 UI 또는 다운로드 안내 여부를 확인하세요."

주의: 이미지 파일 단독 검증 시 서비스 컨텍스트 알 수 없음 → 케이스 C (WARNING)
     검증 API 호출 시 context 파라미터로 서비스 정보 제공 가능
```

### R-04: 가시 라벨 확인

```
조건: detectors["ocr"].status == FOUND
      AND ocr.matched_pattern in AI_LABEL_PATTERNS
      AND ocr.confidence >= 0.80
분류: 사람이 인식할 수 있는 방법
결과: 가시_충족_후보
근거: 시행령 제23조 제2항 — 사람이 인식할 수 있는 방법 (단독으로 충족)

AI_LABEL_PATTERNS (v0, W7에서 확장):
  한국어: ["AI 생성", "AI생성", "인공지능 생성", "AI 제작", "AI 합성",
            "인공지능이 생성", "AI로 생성"]
  영문:   ["AI-generated", "AI generated", "Created by AI", "Made with AI",
            "AI created", "Generated by AI"]
  서비스명 패턴: ["Gemini", "DALL-E", "Midjourney", "Firefly", "Sora"]  # 보조 지표
```

### R-05: 표시 전무 → 불충족

```
조건: detectors["c2pa"].status == NOT_FOUND
      AND detectors["exif"].status == NOT_FOUND
      AND detectors["ocr"].status == NOT_FOUND
      AND detectors["watermark"].status IN [NOT_FOUND, UNKNOWN]
결과: NON_COMPLIANT
근거: 법 제31조 제2항 — 표시 의무 미이행
권고: "AI 생성 표시를 찾을 수 없습니다. 아래 방법 중 하나 이상을 적용하고
      사람 인식 방법(가시 라벨) 또는 기계 판독 방법 + 1회 안내를 추가하세요:
      ① C2PA 매니페스트 삽입  ② EXIF/XMP AI 메타데이터  ③ 가시 라벨(이미지 내 로고)"
```

### R-06: 강건성 불안정 → 경고

```
조건: 어떤 탐지기든 충족_후보 도달
      AND robustness.survival_rate < THRESHOLD
결과: WARNING
근거: 가이드라인 §4 표시 기본원칙 — "AI 생성 결과물이 AI에 의해 생성되었다는
      사실을 인지할 수 있도록 표시" 취지상 유통 중 소실되는 표시는 미달

THRESHOLD 기본값: 0.70 (70% 생존율)
      — 벤치마크(W3) 결과 후 권장값 보완, 설정 가능

권고: "{detector} 표시가 탐지됐으나 {transform_type} 변형 후 생존율이 {rate:.0%}로
      낮습니다. 더 강건한 표시 방식 또는 복수 표시를 권장합니다."
```

### R-07: 딥페이크 강화 표시 검증 (신규)

```
[원문 근거] 가이드라인 §4 이미지 생성물:
  "실제와 구분하기 어려운 생성물(딥페이크)은 명확하게 인식할 수 있는 방법으로써
   사람이 인식할 수 있는 방법만을 적용"

조건: context.is_deepfake_service == True
      OR image_analysis.deepfake_probability >= 0.80  # 딥페이크 감지기 (v1 예정)

서브-케이스 A — 가시 라벨 있음:
  조건: R-04 발동
  결과: 충족 (딥페이크 요건 충족)

서브-케이스 B — 비가시만 있고 딥페이크 확인:
  조건: R-04 미발동 AND (R-01 OR R-02) 발동
  결과: NON_COMPLIANT
  권고: "딥페이크 콘텐츠에는 사람이 명확히 인식할 수 있는 표시 방법만 허용됩니다
        (기계 판독 방식 단독 불가). 이미지 내 가시 라벨('AI 생성' 등)을 추가하세요."

서브-케이스 C — 딥페이크 여부 불명:
  조건: context.is_deepfake_service == None
  결과: WARNING (딥페이크 여부 미확인 경고)

비고: 딥페이크 자동 감지(image_analysis)는 W38 구현 예정. v0에서는 context 파라미터만 사용.
```

---

## 5. 판정 알고리즘

```python
def evaluate(
    detections: list[DetectionResult],
    robustness: SurvivalReport | None,
    context: VerificationContext,
) -> RuleVerdict:

    # R-05: 표시 전무
    all_absent = all(
        d.status in (NOT_FOUND, UNKNOWN)
        for d in detections
    )
    if all_absent:
        return RuleVerdict(NON_COMPLIANT, ["R-05"], ["R-05"],
                           "AI 생성 표시를 찾을 수 없습니다.")

    # 충족 후보 수집
    invisible_candidates = []  # 기계 판독 방식
    visible_candidates = []    # 사람 인식 방식

    if c2pa_valid(detections):    invisible_candidates.append("R-01")
    if exif_flag(detections):     invisible_candidates.append("R-02")
    if visible_label(detections): visible_candidates.append("R-04")

    # R-07: 딥페이크 강화 표시 검증
    if context.is_deepfake_service == True:
        if not visible_candidates:
            return RuleVerdict(NON_COMPLIANT, ["R-07"], ["R-07"],
                               "딥페이크 콘텐츠에는 가시 라벨이 필수입니다.")

    # R-03: 비가시 전용 여부 → 1회 안내 확인
    if invisible_candidates and not visible_candidates:
        if context.download_notice_confirmed == False and context.is_external_distribution:
            return RuleVerdict(NON_COMPLIANT, ["R-03"], ["R-03"],
                               "비가시 표시 + 외부배포 + 안내 없음 → 불충족")
        elif context.download_notice_confirmed is None:
            return RuleVerdict(WARNING, ["R-03"], [],
                               "비가시 표시만 탐지. 다운로드 시 1회 안내 여부를 확인하세요.")
        # download_notice_confirmed == True → 충족으로 계속

    all_candidates = invisible_candidates + visible_candidates

    # R-06: 강건성 경고
    if robustness and robustness.min_survival < THRESHOLD:
        return RuleVerdict(WARNING, all_candidates + ["R-06"], [],
                           f"표시 생존율 {robustness.min_survival:.0%} — 강건성 보강 권장")

    # 충족
    if all_candidates:
        return RuleVerdict(COMPLIANT, all_candidates, [], "표시 요건을 충족합니다.")

    return RuleVerdict(UNKNOWN, [], [], "판정에 필요한 탐지 정보가 부족합니다.")
```

---

## 6. 판정 우선순위 (충돌 해소)

| 우선순위 | 조건 | 최종 판정 |
|---|---|---|
| 1 | R-05 발동 (표시 전무) | NON_COMPLIANT |
| 2 | R-07 발동 (딥페이크 + 비가시 전용) | NON_COMPLIANT |
| 3 | R-03 케이스B (비가시 + 외부배포 + 안내 없음) | NON_COMPLIANT |
| 4 | R-03 케이스C (비가시 + 컨텍스트 불명) | WARNING |
| 5 | R-06 발동 (강건성 임계 미달) | WARNING |
| 6 | R-07 케이스C (딥페이크 여부 불명) | WARNING |
| 7 | R-01/R-02 + 1회 안내 확인 OR R-04 가시 라벨 있음 | COMPLIANT |
| 8 | 모든 탐지기 UNKNOWN | UNKNOWN |

---

## 7. 엣지 케이스

| 케이스 | 처리 방식 |
|---|---|
| C2PA 서명은 있으나 AI assertion 없음 | R-01 미발동 (`has_ai_assertion = False`) |
| OCR 검출됐으나 confidence < 0.80 | R-04 미발동, 탐지기 결과에 `low_confidence` 플래그 |
| SynthID 등 비공개 워터마크 | `watermark.status = UNKNOWN`, 과대주장 금지 |
| EXIF 완전 제거된 이미지 (SNS 재인코딩) | R-02 NOT_FOUND, 강건성 하니스 대상 |
| 서비스 내 이용 (다운로드 기능 없음) | `is_external_distribution = False` → R-03 완화 |
| 가시 라벨이 크롭으로 잘린 경우 | R-06 경고 (강건성 하니스가 탐지) |
| 예술적·창의적 표현물 딥페이크 | `is_artistic_work = True` → R-07 완화 (`WARNING` 하향) |
| 클립보드 복사 | 검증 대상 아님 (가이드라인 명시 제외) |
| 중간 생성물 (편집 중) | 검증 대상 아님 (최종 결과물만) |

---

## 8. 체크리스트 A~E 매핑

| 체크리스트 | 해당 룰 | 구현 위치 |
|---|---|---|
| A: AI 생성 여부 표시 존재 | R-05 (없으면 불충족) | `rules/engine.py` |
| B: 표시 방식 적정성 (비가시 시 1회 안내) | R-03 (컨텍스트 기반 판정) | `rules/engine.py` |
| C: 표시 내용 명확성 (가시 라벨) | R-04 (패턴 매칭) | `detectors/ocr_detector.py` |
| D: 고위험 유형 강화 표시 (딥페이크) | R-07 (사람 인식 방법만) | `rules/engine.py`, W38 확장 |
| E: 표시 지속성·강건성 | R-06 (생존율 임계치) | `robustness/harness.py` |

---

## 9. 미확정 항목

- [ ] R-06 THRESHOLD 기본값 0.70 — 벤치마크(W3) 결과 후 근거 기반 조정
- [ ] EXIF AI 플래그 확인 필드 전체 목록 — W2 포맷 조사 후 확정
- [ ] R-04 AI_LABEL_PATTERNS 확장 — W7 OCR 엔진 구현 시 실측 보완
- [ ] R-07 딥페이크 자동 감지 (image_analysis) — W38 구현 예정
- [ ] VerificationContext API 설계 — 서비스 정보 어떻게 수집·전달할지

---

## 10. 버전 이력

| 버전 | 날짜 | 변경 내용 |
|---|---|---|
| v0.1 | 2026-06-06 | W1 초안 — 전략 문서 기반, 법령 인용구 미확정 |
| v0.2 | 2026-06-06 | W1 완료 — 가이드라인 원문 PDF 기반 전면 갱신. R-03 수정(비가시+1회안내=충족), R-07 신규(딥페이크), VerificationContext 추가, 법령 인용구 확정 |

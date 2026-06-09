# 5분 시작 가이드 / 5-Minute Quickstart

KoAI-Verify로 AI 생성 이미지의 한국 AI 기본법 준수 여부를 5분 안에 확인하세요.

---

## 1단계: 설치 / Step 1: Install

```bash
pip install koai-verify
```

Python 3.10 이상이 필요합니다.

---

## 2단계: CLI로 빠른 검증 / Step 2: Quick Verify via CLI

```bash
koai-verify path/to/image.jpg
```

**판정 결과 / Verdict**

| 판정 | 의미 |
|---|---|
| `COMPLIANT` | 법적 표시 요건 충족 |
| `NON_COMPLIANT` | 미충족 — 조치 필요 |
| `WARNING` | 강건성 미달 — 주의 필요 |
| `UNKNOWN` | 탐지 불가 — 수동 확인 필요 |

```bash
# 사람이 읽기 좋은 요약
koai-verify image.jpg --format summary

# 강건성 배터리 포함 (압축/리사이즈/SNS 재인코딩 시뮬)
koai-verify image.jpg --robustness
```

---

## 3단계: Python API / Step 3: Python API

```python
from koai_verify import verify

# 기본 검증
report = verify("path/to/image.jpg")

# 판정 확인
print(report.verdict)         # Verdict.COMPLIANT 등
print(report.triggered_rules) # ['R-03'] 등

# 한국어 요약
print(report.to_summary())

# JSON 직렬화
import json
print(json.dumps(report.to_json(), indent=2, ensure_ascii=False))
```

---

## 4단계: 결과 해석 / Step 4: Interpret Results

### NON_COMPLIANT — R-03 (가장 흔한 케이스)

```
비가시 워터마크가 발견됐으나 사람 인식 안내 텍스트가 없습니다.
```

**의미**: C2PA 또는 EXIF 비가시 마크가 있지만, 이미지나 UI에 "AI 생성" 텍스트 안내가 없습니다.  
**조치**: 이미지에 가시 라벨("AI 생성" / "AI-generated")을 추가하거나, 서비스 UI에 1회 이상 고지하세요.

### NON_COMPLIANT — R-05

```
어떤 AI 표시도 탐지되지 않았습니다.
```

**의미**: C2PA, EXIF, OCR, 워터마크 중 어느 것도 탐지되지 않았습니다.  
**조치**: 이미지 생성 도구에서 AI 표시 옵션을 활성화하거나, 수동으로 메타데이터를 추가하세요.

### WARNING — R-06

```
강건성 생존율이 임계치 미만입니다.
```

**의미**: 표시는 존재하지만 압축/SNS 재인코딩 후 탐지율이 낮습니다.  
**조치**: 더 강건한 표시 방식(가시 라벨 병행)을 고려하세요.

---

## 5단계: JavaScript/TypeScript SDK / Step 5: JS/TS SDK

```bash
npm install @koai/verify
```

```typescript
import { verify } from "@koai/verify";

const report = await verify("path/to/image.jpg");
console.log(report.verdict);          // "COMPLIANT" | "NON_COMPLIANT" | ...
console.log(report.triggered_rules);  // string[]
```

---

## 웹 플레이그라운드 / Web Playground

```bash
pip install koai-verify[playground]
python playground/app.py
```

브라우저에서 `http://localhost:7860` 을 열어 드래그&드롭으로 이미지를 검증하세요.

---

## 다음 단계 / Next Steps

- [룰 엔진 스펙](rules/rule_engine_spec_v0.md) — R-01~R-07 상세 정의
- [강건성 프로토콜](../benchmarks/protocol_v1.md) — 변형 배터리 설계
- [포맷 지형 조사](format_landscape.md) — 탐지 가능/불가 경계
- [기여 가이드](../CONTRIBUTING.md) — 개발 환경 설정 및 PR 절차

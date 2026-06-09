# KoAI-Verify

**한국 AI 기본법 제31조 표시 의무 검증 오픈소스 SDK**  
*Open-source SDK for verifying AI disclosure requirements under Korea's AI Basic Act Article 31*

[![CI](https://github.com/seokwoo-han/fantastic-octo-meme/actions/workflows/ci.yml/badge.svg)](https://github.com/seokwoo-han/fantastic-octo-meme/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## 개요 / Overview

AI 생성 이미지가 **한국 AI 기본법 제31조** 표시 요건을 충족하는지 자동으로 판정하는 SDK입니다.

This SDK automatically determines whether AI-generated images meet the disclosure requirements of **Korea's AI Basic Act Article 31**.

**주요 기능 / Features**

- C2PA 매니페스트 탐지 / C2PA manifest detection
- EXIF AI 플래그 검사 / EXIF AI flag inspection  
- OCR 기반 가시 라벨 탐지 ("AI 생성" 텍스트) / OCR-based visible label detection
- 강건성 측정 (압축·리사이즈·재인코딩 생존율) / Robustness measurement (compression, resize, re-encoding survival)
- 한국법 룰 엔진 (R-01~R-07) / Korean law rule engine

---

## 빠른 시작 / Quick Start

### 설치 / Installation

```bash
pip install koai-verify
```

### CLI 사용법 / CLI Usage

```bash
# 기본 검증 (JSON 출력)
koai-verify path/to/image.jpg

# 사람이 읽기 좋은 요약 출력
koai-verify path/to/image.jpg --format summary

# 강건성 배터리 포함 검증
koai-verify path/to/image.jpg --robustness
```

**출력 예시 / Example Output**

```json
{
  "image_sha256": "abc123...",
  "verdict": "NON_COMPLIANT",
  "triggered_rules": ["R-03"],
  "detections": {
    "c2pa": "FOUND",
    "exif": "NOT_FOUND",
    "ocr": "NOT_FOUND",
    "watermark": "UNKNOWN"
  },
  "recommendation": "비가시 워터마크가 발견됐으나 사람 인식 안내 텍스트가 없습니다. 가시 라벨 또는 UI 안내를 추가하세요.",
  "timestamp": "2026-08-01T00:00:00Z"
}
```

### Python SDK

```python
from koai_verify import verify

report = verify("path/to/image.jpg")
print(report.verdict)          # COMPLIANT / NON_COMPLIANT / WARNING / UNKNOWN
print(report.to_summary())     # 한국어 요약
print(report.to_json())        # JSON 직렬화
```

### JavaScript / TypeScript SDK

```typescript
import { verify } from "@koai/verify";

const report = await verify("path/to/image.jpg");
console.log(report.verdict);
```

---

## 판정 룰셋 / Rule Engine

| 룰 | 설명 | 판정 |
|---|---|---|
| R-01 | C2PA 매니페스트 존재 + 유효 서명 | 비가시 충족 후보 |
| R-02 | EXIF/XMP AI 플래그 | 비가시 충족 후보 |
| R-03 | 비가시 전용 + 사람 인식 안내 없음 | **NON_COMPLIANT** |
| R-04 | 가시 라벨 "AI 생성" 텍스트 | 가시 충족 후보 |
| R-05 | 어떤 표시도 탐지 불가 | **NON_COMPLIANT** |
| R-06 | 강건성 생존율 < 임계치 | **WARNING** |
| R-07 | 딥페이크 + 비가시 전용 | **NON_COMPLIANT** |

> **핵심**: 비가시 워터마크만 있고 "사람 인식 안내"가 없으면 법적 불충족 (R-03)

---

## 개발 환경 설정 / Development Setup

```bash
# 의존성 설치
poetry install

# 단위 테스트
pytest tests/unit/

# 린트
ruff check . && black --check .

# CLI 직접 실행
koai-verify tests/fixtures/samples/midjourney_sample.jpg
```

---

## 프로젝트 구조 / Project Structure

```
koai_verify/
  detectors/       # C2PA / EXIF / OCR / Watermark 탐지 엔진
  rules/           # 한국법 룰 엔진 (R-01~R-07)
  robustness/      # 강건성 하니스 (변형 배터리)
  report/          # 판정 리포트 포맷터
  api.py           # 고수준 verify() API
  cli.py           # CLI 진입점
sdk/               # JS/TS SDK 래퍼 (@koai/verify)
playground/        # Gradio 웹 플레이그라운드
tests/unit/        # 단위 테스트
docs/              # 법령·기술 문서
```

---

## 기여 / Contributing

기여를 환영합니다! [CONTRIBUTING.md](CONTRIBUTING.md)를 먼저 읽어주세요.

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

## 라이선스 / License

Apache-2.0 — [LICENSE](LICENSE) 참조

---

## 법적 고지 / Legal Notice

이 SDK는 판정 보조 도구입니다. 법적 준수 여부의 최종 판단은 법률 전문가에게 확인하세요.  
*This SDK is a compliance aid tool. Consult a legal professional for final legal compliance determinations.*

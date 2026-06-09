# KoAI-Verify

한국 AI 기본법 제31조 표시 의무 검증 오픈소스 SDK.

AI 생성 이미지가 법적 표시 요건을 충족하는지 판정하고, 강건성(압축·리사이즈·재인코딩 생존율)을 측정합니다.

## 설치

```bash
pip install koai-verify
```

## 사용법

```bash
koai-verify path/to/image.jpg
```

## 개발 환경 설정

```bash
poetry install
pytest tests/unit/
```

## 라이선스

Apache-2.0

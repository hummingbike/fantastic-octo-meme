# 커뮤니티 게시 초안 — GeekNews / 디스콰이엇

> 게시 채널: GeekNews (geek-news.dev) + 디스콰이엇  
> 상태: 초안 (수동 게시 필요)

---

## GeekNews 게시 텍스트

**제목**: KoAI-Verify — 한국 AI 기본법 제31조 표시 의무 검증 오픈소스 SDK

**본문**:

AI 생성 이미지의 표시 의무(한국 AI 기본법 제31조)를 자동으로 검증하는 오픈소스 SDK를 공개합니다.

**주요 기능:**
- C2PA 매니페스트 · EXIF AI 플래그 · OCR 가시 라벨 탐지
- 한국법 룰 엔진 (R-01~R-07, 과기정통부 가이드라인 기반)
- 강건성 벤치마크: SNS 재인코딩 후 생존율 측정 (Instagram/Twitter/KakaoTalk)
- CLI + Python SDK + JS/TS SDK

**핵심 발견 (갭 리포트):**
- 주요 AI 도구 대다수: 표시 의무 불충족
- SNS 업로드 시 C2PA/EXIF 100% 소거 → 가시 라벨만 생존
- R-03 함정: C2PA 마크만 있고 사람 안내 없으면 법적 불충족

```bash
pip install koai-verify
koai-verify image.jpg
```

GitHub: https://github.com/hummingbike/fantastic-octo-meme  
라이선스: Apache-2.0

---

## 디스콰이엇 게시 텍스트

**제품명**: KoAI-Verify

**한 줄 소개**: AI 이미지 법적 표시 의무를 자동으로 검증하는 오픈소스 SDK

**설명**:

한국 AI 기본법 시행이 다가오면서 "우리 서비스의 AI 생성 이미지가 법적 표시를 제대로 하고 있나?" 를 검증하기 어려워서 직접 만들었습니다.

`pip install koai-verify && koai-verify image.jpg` 로 COMPLIANT / NON_COMPLIANT / WARNING 판정을 즉시 받을 수 있습니다.

주요 도구 9종을 분석한 갭 리포트도 함께 공개합니다. SNS에 올리면 C2PA/EXIF가 100% 소거된다는 점이 가장 충격적인 발견이었습니다.

1인 개발, Apache-2.0, 피드백 환영합니다.

**카테고리**: 개발 도구 / 컴플라이언스  
**링크**: https://github.com/hummingbike/fantastic-octo-meme

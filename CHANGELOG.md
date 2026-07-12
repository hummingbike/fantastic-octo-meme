# Changelog

KoAI-Verify의 주요 변경 사항을 기록한다. [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식,
[SemVer](https://semver.org/lang/ko/)를 따른다.

## [0.2.0] — 2026-07-12

### Added

- **W17** SDK 오류 체계 — Python `ImageLoadError` 서브클래스 5종, JS `VerifyError.code`, `docs/faq.md`
- **W18** 통합 예제 — Next.js App Router (`docs/examples/nextjs_example.ts`), FastAPI (`docs/examples/fastapi_example.py`)
- **W19** TTA 표준화 참여 — TC010 컨택 정보 모듈(`koai_verify/standards/tta_contact.py`), 갭 분석·제안서 초안
- **W20** 호스팅 검증 API v0 — FastAPI `POST /v0/verify`, API 키 인증, 사용량 측정, Docker 구성
- **W21** 가격 티어 — Free/Pro/Enterprise 정의(`server/pricing.py`), `GET /v0/pricing`
- **W22** 공유 배지/리포트 — SVG 배지(`report/badge.py`), `GET /v0/share/{id}`, `GET /v0/badge/{id}.svg`
- **W24** 규제 변경 모니터링 — 과기정통부·NIA·TTA·법령정보센터 4개 소스 주간 자동 점검(`standards/regulation_monitor.py`)
- **W25** 채택 지표 실측 — PRD §5 지표 수집·평가(`analysis/adoption_metrics.py`), Q2 회고(`docs/retrospective_q2.md`)

### Fixed

- **W25** 규제 모니터 거짓 양성 — fetch 타임아웃을 "변경 감지"로 오인해 매주 이슈를 생성하던 버그 수정
  (fetch 실패는 `FETCH_ERROR`로 기록하고 변경으로 간주하지 않음, 워크플로는 exit 1일 때만 이슈 생성)

## [0.1.0] — 2026-06-09

### Added

- 탐지 엔진 4종 — C2PA 매니페스트, EXIF/XMP AI 플래그, OCR 가시 라벨, 오픈 워터마크(항상 UNKNOWN 명시)
- 한국법 룰 엔진 — AI 기본법 제31조 기반 R-01~R-07, 판정 COMPLIANT/NON_COMPLIANT/WARNING/UNKNOWN
- 강건성 하니스 — 20종 변형 배터리(JPEG/WebP/리사이즈/크롭/SNS 재인코딩 시뮬), 생존율 매트릭스
- CLI `koai-verify <image>` — `--format json|summary`, `--robustness`
- Python SDK (`pip install koai-verify`), JS/TS SDK 래퍼, Gradio 웹 플레이그라운드
- 강건성 벤치마크 공개(`benchmarks/results/`), 갭 리포트 v1

[0.2.0]: https://github.com/hummingbike/fantastic-octo-meme/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/hummingbike/fantastic-octo-meme/releases/tag/v0.1.0

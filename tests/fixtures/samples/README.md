# tests/fixtures/samples/ — 도구별 샘플 이미지 디렉터리

## 용도

각 AI 이미지 생성 도구의 출력물을 수집해 메타데이터 갭을 분석한다.

## 디렉터리 구조

```
samples/
  stable_diffusion/    # Stable Diffusion AUTOMATIC1111 출력
  comfyui/             # ComfyUI 출력
  midjourney/          # Midjourney 출력 (스크린샷 포함)
  dalle3/              # DALL-E 3 출력
  firefly/             # Adobe Firefly 출력 (C2PA 예시)
  drapart/             # 드랩아트 출력 (W4 수집 예정)
  genape/              # GenApe 출력 (W4 수집 예정)
  vela/                # 벨라 출력 (W4 수집 예정)
  jeditor/             # 제디터 출력 (W4 수집 예정)
```

## 수집 지침

- 저작권 클리어한 이미지만 커밋 (직접 생성한 테스트 이미지)
- 파일명: `{tool}_{index:02d}.jpg` (예: `stable_diffusion_01.jpg`)
- 개인 정보 포함 프롬프트 사용 금지
- 각 도구당 최소 5장 수집 권장

## 합성 픽스처 (synthetic/)

실제 샘플 수집 전, 공개 문서 기반 합성 픽스처가 `synthetic/` 에 있다.
이 파일들은 각 도구의 메타데이터 패턴을 시뮬레이션한다.

## 한국 도구 수집 현황 (2026-06-07 기준)

| 도구 | 수집 상태 | 메타데이터 특성 |
|---|---|---|
| 드랩아트 | 🔴 미수집 (W4) | 미확인 |
| GenApe | 🔴 미수집 (W4) | 미확인 |
| 벨라 | 🔴 미수집 (W4) | 미확인 |
| 제디터 | 🔴 미수집 (W4) | 미확인 |
| Stable Diffusion | 🟢 합성 픽스처 | EXIF Software + UserComment |
| ComfyUI | 🟢 합성 픽스처 | EXIF UserComment (workflow JSON) |
| Midjourney | 🟢 합성 픽스처 | 마킹 없음 |
| DALL-E 3 | 🟢 합성 픽스처 | 마킹 없음 |
| Adobe Firefly | 🟡 합성 픽스처 | C2PA 표시됨 (서명 없는 시뮬) |

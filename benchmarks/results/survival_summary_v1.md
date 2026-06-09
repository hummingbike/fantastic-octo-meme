# KoAI-Verify 강건성 벤치마크 결과 v1

> 생성일: 2026-06-09  
> 픽스처: 9개 이미지 (합성 픽스처 기반)  
> 변형: 20종 / 탐지 포맷: 4종 (C2PA·EXIF·가시라벨·오픈워터마크)  
> **주의**: 이 결과는 합성 테스트 픽스처 기반입니다. 실제 AI 생성 이미지 결과와 다를 수 있습니다.

---

## 핵심 요약

| 탐지 포맷 | 평균 생존율 | 비고 |
|---|---|---|
| C2PA 매니페스트 | 0.0% | ⚠️ R-06 경고 트리거 |
| EXIF AI 플래그 | 0.0% | ⚠️ R-06 경고 트리거 |
| 가시 라벨 (OCR) | 측정 불가 | 원본 탐지 FOUND 이미지 없음 |
| 오픈 워터마크 | 측정 불가 | 항상 UNKNOWN |

**R-06 평가**: 임계치 80% — 측정 40셀 중 임계치 미달 40셀

---

## SNS 재인코딩 생존율 (핵심)

| 플랫폼 | C2PA | EXIF | 가시라벨 | 비고 |
|---|---|---|---|---|
| Instagram | 0.0% | 0.0% | N/A | ⚠️ 완전 소거 위험 |
| Twitter/X | 0.0% | 0.0% | N/A | ⚠️ 완전 소거 위험 |
| KakaoTalk 채팅 | 0.0% | 0.0% | N/A | ⚠️ 완전 소거 위험 |
| KakaoTalk 프로필 | 0.0% | 0.0% | N/A | ⚠️ 완전 소거 위험 |

---

## 변형별 상세 생존율 — EXIF AI 플래그

| 변형 | 생존율 |
|---|---|
| jpeg_compress_q95 | 0.0% |
| jpeg_compress_q80 | 0.0% |
| jpeg_compress_q60 | 0.0% |
| jpeg_compress_q40 | 0.0% |
| jpeg_compress_q20 | 0.0% |
| webp_convert_q90 | 0.0% |
| webp_convert_q70 | 0.0% |
| webp_convert_q50 | 0.0% |
| resize_75pct | 0.0% |
| resize_50pct | 0.0% |
| resize_25pct | 0.0% |
| crop_center_90pct | 0.0% |
| crop_center_70pct | 0.0% |
| crop_random_80pct | 0.0% |
| sns_instagram | 0.0% |
| sns_twitter | 0.0% |
| sns_kakaotalk_chat | 0.0% |
| sns_kakaotalk_profile | 0.0% |
| screenshot_96dpi | 0.0% |
| screenshot_72dpi | 0.0% |

---

## 변형별 상세 생존율 — 가시 라벨 (OCR)

| 변형 | 생존율 |
|---|---|
| jpeg_compress_q95 | N/A |
| jpeg_compress_q80 | N/A |
| jpeg_compress_q60 | N/A |
| jpeg_compress_q40 | N/A |
| jpeg_compress_q20 | N/A |
| webp_convert_q90 | N/A |
| webp_convert_q70 | N/A |
| webp_convert_q50 | N/A |
| resize_75pct | N/A |
| resize_50pct | N/A |
| resize_25pct | N/A |
| crop_center_90pct | N/A |
| crop_center_70pct | N/A |
| crop_random_80pct | N/A |
| sns_instagram | N/A |
| sns_twitter | N/A |
| sns_kakaotalk_chat | N/A |
| sns_kakaotalk_profile | N/A |
| screenshot_96dpi | N/A |
| screenshot_72dpi | N/A |

---

## 분석 이미지 목록

| 이미지 | C2PA | EXIF | OCR |
|---|---|---|---|
| c2pa_test_C.jpg | FOUND | NOT_FOUND | UNKNOWN |
| ocr_aigc.jpg | NOT_FOUND | NOT_FOUND | UNKNOWN |
| ocr_en_label.jpg | NOT_FOUND | NOT_FOUND | UNKNOWN |
| ocr_ko_ascii_label.jpg | NOT_FOUND | NOT_FOUND | UNKNOWN |
| ocr_made_with_ai.jpg | NOT_FOUND | NOT_FOUND | UNKNOWN |
| ocr_no_label.jpg | NOT_FOUND | NOT_FOUND | UNKNOWN |
| midjourney_01.jpg | NOT_FOUND | NOT_FOUND | UNKNOWN |
| stable_diffusion_01.jpg | NOT_FOUND | FOUND | UNKNOWN |
| firefly_01.jpg | NOT_FOUND | FOUND | UNKNOWN |

---

## 방법론

- **변형 배터리**: 20종 (`benchmarks/transform_spec.py` `TRANSFORM_BATTERY`)
- **탐지 포맷**: C2PA (c2pa-python), EXIF (piexif/Pillow), 가시라벨 (OCR 패턴), 오픈워터마크 (UNKNOWN)
- **생존 기준**: 원본 FOUND → 변형 후 FOUND 이면 생존
- **픽스처**: 합성 JPEG (실제 AI 도구 출력 아님 — 실측치는 gap_report_v1.md 참조)
- **R-06 임계치**: 80% — 미달 시 WARNING 판정

자세한 프로토콜: [benchmarks/protocol_v1.md](../protocol_v1.md)
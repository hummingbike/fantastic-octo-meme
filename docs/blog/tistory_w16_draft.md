# [기술 블로그] 한국 AI 기본법 준수 검증기를 오픈소스로 공개합니다

> 게시 채널: Tistory 기술 블로그  
> 상태: 초안 (수동 게시 필요)  
> 태그: AI기본법, 오픈소스, 검증기, C2PA, EXIF, 한국AI규제

---

## 한국 AI 기본법 제31조 — 개발자가 알아야 할 것

올해 말 계도기간이 끝나면, AI가 생성한 이미지를 서비스에 사용하는 모든 사업자는
**"이 이미지는 AI가 만들었습니다"** 라는 표시를 해야 합니다.

구체적으로 어떻게 해야 할까요? 법령 원문에는 이렇게 나와 있습니다:

> 제31조 ② 인공지능사업자는 ... AI 생성물임을 알 수 있도록 표시하여야 한다.

문제는 **"어떤 표시를 어디에 어떻게 해야 하는지"** 를 개발자가 직접 검증하기가 어렵다는 겁니다.
그래서 **KoAI-Verify** 를 만들었습니다.

---

## KoAI-Verify 가 하는 일

```bash
pip install koai-verify
koai-verify path/to/image.jpg
```

실행하면 이런 판정이 나옵니다:

```json
{
  "verdict": "NON_COMPLIANT",
  "triggered_rules": ["R-03"],
  "detections": {
    "c2pa": "FOUND",
    "exif": "NOT_FOUND",
    "ocr": "NOT_FOUND"
  },
  "recommendation": "비가시 워터마크가 발견됐으나 사람 인식 안내 텍스트가 없습니다."
}
```

4가지 탐지 방식으로 표시 여부를 확인합니다:

| 탐지 방식 | 확인 내용 |
|---|---|
| C2PA 매니페스트 | Adobe·구글 등이 쓰는 디지털 서명 |
| EXIF/XMP AI 플래그 | 메타데이터에 숨겨진 AI 생성 표시 |
| OCR 가시 라벨 | 이미지에 직접 찍힌 "AI 생성" 텍스트 |
| 오픈 워터마크 | Tree-Ring, StegaStamp 등 (UNKNOWN) |

---

## 핵심 판정 규칙 — R-03

가장 중요한 규칙은 **R-03** 입니다:

> **비가시 워터마크(C2PA/EXIF)만 있고 사람이 인식할 수 있는 안내가 없으면 → 불충족**

즉, C2PA 매니페스트를 이미지에 심었더라도 사용자에게 "이건 AI가 만든 이미지입니다"라고
알리지 않으면 법적으로 불충족입니다. 과기정통부 가이드라인 §4에 명시된 내용입니다.

---

## 갭 리포트: 주요 AI 도구 9종 분석

한국에서 많이 쓰는 AI 이미지 생성 도구들이 실제로 표시 의무를 지키고 있을까요?

**분석 결과 (예비 측정, 합성 픽스처 기반):**

| 도구 | C2PA | EXIF AI | 가시 라벨 | 판정 |
|---|---|---|---|---|
| Adobe Firefly | ✓ | ✓ | △ | 비가시 전용 → R-03 위험 |
| Stable Diffusion | ✗ | △ | ✗ | NON_COMPLIANT |
| ComfyUI | ✗ | ✗ | ✗ | NON_COMPLIANT |
| Midjourney | ✗ | ✗ | ✗ | NON_COMPLIANT |
| DALL-E 3 | ✗ | ✗ | ✗ | NON_COMPLIANT |

더 자세한 내용은 [갭 리포트 v1](https://github.com/hummingbike/fantastic-octo-meme/blob/main/docs/gap_report_v1.md) 에서 확인할 수 있습니다.

---

## SNS에 올리면 사라진다 — 강건성 0% 문제

가장 심각한 발견은 **SNS 소거 문제**입니다.

이미지를 Instagram, Twitter, KakaoTalk에 올리면 **C2PA와 EXIF가 100% 제거됩니다.**

| 플랫폼 | C2PA 생존율 | EXIF 생존율 |
|---|---|---|
| Instagram | 0% | 0% |
| Twitter/X | 0% | 0% |
| KakaoTalk 채팅 | 0% | 0% |

비가시 워터마크에만 의존하는 도구는 SNS 유통 이후 추적이 완전히 불가능해집니다.
**가시 라벨("AI 생성" 텍스트)이 유일하게 살아남는 방식**입니다.

---

## 오픈소스로 공개 — 같이 만들어요

```bash
# 설치
pip install koai-verify

# 또는 소스에서
git clone https://github.com/hummingbike/fantastic-octo-meme
poetry install
```

**Python SDK:**
```python
from koai_verify import verify
report = verify("image.jpg")
print(report.verdict)  # COMPLIANT / NON_COMPLIANT / WARNING / UNKNOWN
```

**GitHub Actions 통합:**
```yaml
- name: AI 표시 의무 검증
  run: pip install koai-verify && koai-verify assets/*.jpg
```

Apache-2.0 라이선스 — 기업 도입도 자유롭게.

---

## 앞으로 계획

- **W17-18**: 초기 통합 피드백 반영
- **W20**: 호스팅 검증 API v0 (API 키, 셀프서브)
- **W27-29**: 강건 비가시 워터마크 코어 (SNS에서도 살아남는 마킹)

규제 계도기간이 끝나기 전에, 미리 준비하는 팀에게 도움이 되면 좋겠습니다.

---

**링크:**
- GitHub: https://github.com/hummingbike/fantastic-octo-meme
- 갭 리포트: docs/gap_report_v1.md
- 강건성 벤치마크: benchmarks/results/survival_summary_v1.md

# format_landscape.md — AI 표시 포맷 지형 조사

> W2 산출물 | 작성일: 2026-06-07 | 담당: seokwoo han
> 기반 문서: [rule_engine_spec_v0.md](rules/rule_engine_spec_v0.md) · [PRD.md](../PRD.md)

---

## 요약

| 포맷 | 탐지 가능 | 한국 도구 채택 | SNS 생존율 | SDK 기본 판정 |
|---|---|---|---|---|
| C2PA 매니페스트 | ✅ c2pa-python | Adobe Firefly만 | 낮음 (재인코딩 시 유실) | `FOUND` / `NOT_FOUND` |
| EXIF UserComment | ✅ piexif | SD 계열 일부 | 낮음 (스크린샷 시 유실) | `FOUND` / `NOT_FOUND` |
| XMP AI 메타데이터 | ✅ Pillow | SD 계열 일부 | 낮음 | `FOUND` / `NOT_FOUND` |
| 가시 라벨 (OCR) | ✅ easyocr/tesseract | 일부 (수동) | 높음 (이미지 내 텍스트) | `FOUND` / `NOT_FOUND` |
| SynthID (Google) | ❌ 비공개 API | 없음 | N/A | `UNKNOWN` |
| Stable Signature | 조건부 ✅ | 없음 | 중간 | `UNKNOWN` (W7 대상) |
| Tree-Ring | 조건부 ✅ | 없음 | 중간 | `UNKNOWN` (키 없으면) |
| HiDDeN | 조건부 ✅ | 없음 | 낮음 | `UNKNOWN` |
| Midjourney 워터마크 | ❌ 없음 | N/A | N/A | `UNKNOWN` |
| DALL-E 워터마크 | ❌ 없음 | N/A | N/A | `UNKNOWN` |

---

## 1. C2PA 매니페스트

### 1.1 개요

C2PA(Coalition for Content Provenance and Authenticity)는 Adobe, Microsoft, Google, Arm 등이 주도하는 개방형 표준으로, 이미지 파일 내에 암호화 서명된 "누가 어디서 만들었나" 메타데이터를 삽입한다.

### 1.2 기술 구조

```
JPEG 파일
  └── JUMBF 박스 (C2PA Manifest Store)
        ├── Manifest #1
        │     ├── claim_generator: "Adobe Firefly/2.0"
        │     ├── assertions:
        │     │     ├── c2pa.actions (생성 이력)
        │     │     ├── c2pa.hash.data (파일 해시)
        │     │     └── c2pa.training-mining (AI 학습 동의)
        │     └── signature_info (X.509 인증서)
        └── active_manifest: Manifest #1
```

### 1.3 Python 탐지 (c2pa-python 0.32.x)

```python
import c2pa
import io

def read_c2pa(image_path: str) -> dict | None:
    with open(image_path, "rb") as f:
        stream = io.BytesIO(f.read())
    try:
        with c2pa.Reader("image/jpeg", stream) as reader:
            return reader.json()
    except c2pa.C2paError:
        return None  # 매니페스트 없음 → NOT_FOUND
```

### 1.4 지원 도구 (2026년 기준)

| 도구 | C2PA 삽입 | 버전 |
|---|---|---|
| Adobe Firefly | ✅ | 모든 버전 |
| Adobe Photoshop (생성형 채우기) | ✅ | 24.6+ |
| Microsoft Designer | ✅ | 베타 |
| Stable Diffusion (공식) | ❌ | - |
| Midjourney | ❌ | - |
| DALL-E 3 | ❌ | - |

### 1.5 생존율 특성

| 변형 | C2PA 생존 | 비고 |
|---|---|---|
| 원본 그대로 복사 | ✅ | 메타데이터 보존 |
| JPEG 재압축 (q=80) | ❌ | JUMBF 박스 유실 |
| WebP 변환 | ❌ | 컨테이너 변경 |
| 스크린샷 (캡처) | ❌ | 픽셀만 추출 |
| SNS 업로드 후 다운로드 | ❌ | 모든 주요 SNS |

**결론**: C2PA는 직접 파일 전달에서만 신뢰성이 있다. SNS 공유 시나리오에서는 보조 표시가 필수다.

---

## 2. EXIF / XMP AI 메타데이터

### 2.1 범용 표준 현황

2026년 기준, AI 생성 이미지를 위한 단일 EXIF 표준은 없다. IPTC Photo Metadata Working Group이 논의 중이나 미확정 상태.

### 2.2 탐지 대상 필드

**EXIF IFD 필드**

| 필드 | Tag | 용도 |
|---|---|---|
| `UserComment` | 0x9286 | AI 생성 여부 텍스트 기재 (가장 흔함) |
| `MakerNote` | 0x927C | 도구 고유 바이너리 메타 |

**0th IFD 필드**

| 필드 | Tag | 용도 |
|---|---|---|
| `ImageDescription` | 0x010E | 이미지 설명 ("AI Generated Image") |
| `Software` | 0x0131 | 생성 도구명 ("Stable Diffusion 2.1") |
| `Artist` | 0x013B | 제작자 (AI 표기 경우 있음) |
| `Copyright` | 0x8298 | AI 생성 저작권 고지 |

**XMP 네임스페이스**

| 네임스페이스 | URI | 탐지 대상 |
|---|---|---|
| `dc` | `http://purl.org/dc/elements/1.1/` | `dc:description` |
| `xmpRights` | `http://ns.adobe.com/xap/1.0/rights/` | `UsageTerms` |
| `Iptc4xmpCore` | `http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/` | `Subject` |
| Stable Diffusion | `http://ns.adobe.com/xap/1.0/` | `parameters` (프롬프트) |

### 2.3 도구별 EXIF 패턴

| 도구 | 삽입 필드 | 값 예시 | 탐지 가능 |
|---|---|---|---|
| Stable Diffusion (AUTOMATIC1111) | Software + UserComment(XMP) | `"Stable Diffusion"` | ✅ |
| ComfyUI | UserComment | workflow JSON | ✅ (파싱 필요) |
| Adobe Firefly | C2PA (EXIF 아님) | - | ✅ (C2PA로) |
| Midjourney | **없음** | - | ❌ UNKNOWN |
| DALL-E 3 | **없음** | - | ❌ UNKNOWN |
| Bing Image Creator | **없음** | - | ❌ UNKNOWN |

### 2.4 UserComment 디코딩 규칙

```python
def decode_user_comment(raw: bytes) -> str | None:
    prefixes = {
        b"ASCII\x00\x00\x00": "ascii",
        b"UNICODE\x00": "utf-16-le",
    }
    for prefix, enc in prefixes.items():
        if raw.startswith(prefix):
            return raw[len(prefix):].decode(enc).rstrip("\x00").strip()
    return raw.decode("latin-1").strip()
```

### 2.5 생존율 특성

EXIF 메타데이터는 JPEG 재압축 시 일반적으로 보존되지만, SNS 플랫폼은 대부분 메타데이터를 제거한다.

| 변형 | EXIF 생존 |
|---|---|
| JPEG 재압축 | 도구 의존 (보통 보존) |
| 스크린샷 | ❌ 완전 유실 |
| Instagram 업로드 | ❌ 제거 |
| Twitter/X 업로드 | ❌ 제거 |
| KakaoTalk 전송 | ❌ 제거 |

---

## 3. SynthID 및 비공개 워터마크

### 3.1 SynthID (Google DeepMind)

- **방식**: 주파수 도메인 비가시 워터마크 (Shazam-like 접근)
- **탐지 API**: 비공개 — Google Cloud Vision API 일부로 통합 예정이나 개방 미정
- **공개 문헌**: [SynthID 논문 (Nature, 2024)](https://www.nature.com/articles/s41586-024-08025-4) — 원리만 공개, 가중치·API 미공개
- **SDK 판정**: `UNKNOWN` (탐지 불가 명시)

### 3.2 Stable Signature (Meta FAIR)

- **방식**: Latent Diffusion 디코더에 미세조정된 비가시 워터마크
- **코드 공개**: [facebookresearch/stable_signature](https://github.com/facebookresearch/stable_signature)
- **탐지 조건**: 키+모델 가중치 필요 → 키 없으면 `UNKNOWN`
- **W7 통합 후보**: 오픈 소스 워터마크 탐지 모듈에서 검토

### 3.3 UNKNOWN 처리 정책

```
탐지 불가 비가시 워터마크 발견 여부 → UNKNOWN
UNKNOWN ≠ NON_COMPLIANT
UNKNOWN → 추가 표시(가시 라벨/EXIF 등) 여부로 최종 판정
```

**중요**: SynthID가 있을 수 있으나 탐지 못 한다고 해서 "없다"고 판정하면 안 된다.

---

## 4. 오픈 워터마크 패턴

### 4.1 주요 연구 워터마크

| 이름 | 방식 | JPEG q50 생존 | 코드 | W7 통합 |
|---|---|---|---|---|
| Tree-Ring | 주파수 도메인 | ✅ | [공개](https://github.com/YuxinWenRick/tree-ring-watermark) | 검토 |
| HiDDeN | 공간 도메인 신경망 | ❌ | [공개](https://github.com/jbutt/HiDDeN) | 낮은 우선순위 |
| StegaStamp | 공간 도메인 | ✅ (물리 인쇄 설계) | [공개](https://github.com/tancik/StegaStamp) | 검토 |
| Stable Signature | 주파수 도메인 | ✅ | [공개](https://github.com/facebookresearch/stable_signature) | 우선 검토 |
| IMATAG | 공간 도메인 | ✅ | 비공개 상용 | - |

### 4.2 한국 도구 채택 현황

**2026년 6월 기준: 한국 AI 이미지 도구 중 오픈 워터마크를 채택한 곳 없음.**

- 드랩아트, GenApe, 벨라, 제디터 모두 워터마크 미채택 (W4 샘플 분석 예정)

---

## 5. 가시 라벨 패턴

### 5.1 탐지 패턴 목록

**한국어 패턴**

```
AI\s*생성
AI\s*로\s*생성
AI\s*로\s*만들어진
인공지능\s*생성
인공지능\s*이\s*만든
AI\s*제작
AI\s*콘텐츠
생성\s*형\s*AI
```

**영문 패턴**

```
AI[\s\-]?[Gg]enerated
[Mm]ade\s+with\s+AI
[Cc]reated\s+(by|with)\s+AI
AI[\s\-]?[Cc]reated
AIGC
\[AI\]
#AI[Gg]enerated
AI[\s\-]produced
```

### 5.2 탐지 방법

- **OCR 엔진**: easyocr (한/영 지원, GPU 불필요) — W7 구현 예정
- **패턴 매칭**: 정규식 (대소문자 무관, `re.IGNORECASE`)
- **위치 힌트**: 이미지 하단/모서리 우선 탐색 → 탐지율 향상

### 5.3 법적 충족 요건 (R-04 연계)

가시 라벨이 탐지되면 R-04 충족. 단:
- 라벨이 이미지 외부(웹페이지 텍스트, 캡션)에만 있는 경우 → 이미지 자체는 불충족 가능
- SDK는 이미지 픽셀 내 라벨만 탐지 (캡션/설명 텍스트는 별도 V-03 확장 필요)

---

## 6. 탐지 불가 케이스 → UNKNOWN 처리

| 케이스 | 이유 | SDK 반환 |
|---|---|---|
| SynthID 워터마크 의심 | 비공개 API | `UNKNOWN` |
| 오픈 워터마크 (키 없음) | 키 필요 | `UNKNOWN` |
| Midjourney 생성 이미지 | 마킹 없음 | `UNKNOWN` |
| DALL-E 3 생성 이미지 | 마킹 없음 | `UNKNOWN` |
| 손상/잘린 C2PA | 서명 검증 실패 | `UNKNOWN` |

**정책**: UNKNOWN은 과대주장 금지 원칙의 핵심. 탐지 못 한 것을 "없다"고 말하지 않는다.

---

## 7. 탐지 엔진 구현 우선순위 (W6–W7 참고)

| 엔진 | 구현 시점 | 라이브러리 | 커버 포맷 |
|---|---|---|---|
| C2PA 탐지기 | W6 | c2pa-python | Adobe Firefly, Microsoft Designer |
| EXIF 탐지기 | W6 | piexif + Pillow | Stable Diffusion, ComfyUI |
| OCR 가시 라벨 탐지기 | W7 | easyocr | 한/영 라벨 텍스트 |
| 오픈 워터마크 탐지기 | W7 | stable_signature (우선) | Meta 계열 |
| 비공개 워터마크 | 구현 없음 | - | → UNKNOWN 반환 |

---

## 부록: 갱신 일정

- W4: 드랩아트·GenApe·벨라·제디터 샘플 분석 후 도구별 갭 반영
- W7: Stable Signature 통합 평가 후 탐지 가능 여부 재분류
- 표준 변경 모니터링: W25 자동화 예정

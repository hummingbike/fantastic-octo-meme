# FAQ — KoAI-Verify 자주 묻는 질문

> 문제가 해결되지 않으면 [GitHub Issues](https://github.com/hummingbike/fantastic-octo-meme/issues)에 리포트해 주세요.

---

## 설치

### `pip install koai-verify` 후 `koai-verify` 명령어를 찾을 수 없어요

가상 환경이 활성화되어 있는지 확인하세요.

```bash
# venv 사용 시
source .venv/bin/activate
koai-verify --version

# 또는 Python 모듈로 직접 실행
python -m koai_verify.cli --version
```

Python 경로가 PATH 에 없는 경우 아래처럼 직접 실행할 수 있습니다.

```bash
python -m koai_verify.cli path/to/image.jpg
```

JS SDK 를 쓰는 경우 `KOAI_VERIFY_CMD` 환경 변수로 경로를 지정하세요.

```bash
KOAI_VERIFY_CMD="python -m koai_verify.cli" node your_script.js
```

---

### Python 3.9 에서 설치했는데 오류가 나요

koai-verify 는 **Python 3.10 이상**이 필요합니다. `python --version` 으로 버전을 확인하세요.

```bash
python --version   # Python 3.10.x 이상이어야 합니다
```

---

### `ImportError: No module named 'PIL'` 오류가 나요

Pillow 가 설치되지 않았습니다. `pip install koai-verify` 를 다시 실행하거나 수동으로 설치하세요.

```bash
pip install Pillow
```

---

## 오류 메시지 해석

### `ImageNotFoundError: 파일 없음: ...`

지정한 경로에 파일이 없습니다. 경로와 파일 이름을 확인하세요.

```python
from koai_verify import verify, ImageNotFoundError

try:
    report = verify("image.jpg")
except ImageNotFoundError as e:
    print(f"파일을 찾을 수 없음: {e}")
```

---

### `UrlNotAllowedError: URL 로드 금지 ...`

보안 정책(SSRF 방지)으로 URL 은 허용하지 않습니다. 이미지를 로컬에 다운로드한 뒤 경로를 전달하세요.

```python
import urllib.request

urllib.request.urlretrieve("https://example.com/image.jpg", "/tmp/image.jpg")
report = verify("/tmp/image.jpg")
```

---

### `UnsupportedFormatError: 지원하지 않는 포맷 ...`

JPEG · PNG · WebP 만 지원합니다. BMP, GIF, TIFF 등은 미지원입니다.  
이미지를 변환한 뒤 재검증하세요.

```bash
# ImageMagick 으로 변환
convert input.bmp output.jpg
koai-verify output.jpg
```

---

### `ImageTooLargeError: 이미지 크기 초과 ...`

50 MB 초과 이미지는 거부됩니다. 이미지를 압축하거나 리사이즈하세요.

```python
from PIL import Image

img = Image.open("huge.jpg")
img.thumbnail((4096, 4096))
img.save("resized.jpg", quality=85)
```

---

### `ImageCorruptedError: 이미지 디코딩 실패 ...`

파일이 손상되었거나 확장자와 실제 포맷이 다릅니다. `file` 명령으로 실제 포맷을 확인하세요.

```bash
file suspicious.jpg   # JPEG image data ... 가 아니면 손상된 파일
```

---

## 판정 결과 해석

### `NON_COMPLIANT` 가 나왔어요. 무엇을 해야 하나요?

리포트의 `failing_rules` 와 `recommendation` 필드를 확인하세요.

| 실패 룰 | 원인 | 조치 |
|---|---|---|
| R-03 | 비가시 마크만 있고 사람 인식 안내 없음 | 가시 라벨("AI 생성") 또는 UI 안내 팝업 추가 |
| R-05 | 어떤 표시도 탐지 안 됨 | C2PA, EXIF 태그 또는 가시 라벨 추가 |
| R-07 | 딥페이크 + 비가시 전용 | 반드시 가시 라벨 + 사람 인식 안내 병행 |

---

### `UNKNOWN` 이 나왔어요

탐지기가 판정을 내리기 위한 충분한 정보를 얻지 못했습니다.  
이미지가 올바른 포맷인지, C2PA 매니페스트가 손상되지 않았는지 확인하세요.  
`UNKNOWN` 은 "위반 없음"을 의미하지 않습니다.

---

### SynthID 이미지를 검증하면 항상 `UNKNOWN` 이에요

SynthID 는 Google 의 비공개 비가시 워터마크로, 탐지 알고리즘이 공개되어 있지 않습니다.  
현재 공개된 방법으로는 탐지가 불가능하며, `UNKNOWN` 반환이 정확한 동작입니다.

---

## 강건성 테스트

### `--robustness` 옵션이 너무 느려요

강건성 배터리는 20종 변형 × 탐지기 수만큼 반복 실행하므로 수십 초가 걸릴 수 있습니다.  
CI 에서는 선택적으로만 실행하는 것을 권장합니다.

```yaml
# GitHub Actions 예: PR 에서는 건너뛰고 릴리즈 브랜치에서만 실행
- run: koai-verify image.jpg --robustness
  if: startsWith(github.ref, 'refs/tags/')
```

---

## JS / Node.js SDK

### `VerifyError: koai-verify CLI 를 찾을 수 없습니다` (code: `CLI_NOT_FOUND`)

Python SDK 가 설치되어 있지 않거나 PATH 에 없습니다.

```bash
pip install koai-verify
# 또는 경로 직접 지정
KOAI_VERIFY_CMD="python -m koai_verify.cli" node your_script.js
```

---

### 오류 코드로 분기 처리하는 방법

```typescript
import { verify, VerifyError } from "@koai/verify";

try {
  const report = verify("/path/to/image.jpg");
} catch (e) {
  if (e instanceof VerifyError) {
    switch (e.code) {
      case "CLI_NOT_FOUND":
        console.error("koai-verify CLI 미설치 — pip install koai-verify");
        break;
      case "IMAGE_NOT_FOUND":
        console.error("이미지 파일 없음:", e.message);
        break;
      case "JSON_PARSE_ERROR":
        console.error("SDK 버전 불일치 가능성:", e.message);
        break;
      default:
        console.error("알 수 없는 오류:", e.message);
    }
  }
}
```

---

## 기타

### 한국 AI 기본법 제31조 시행일은 언제인가요?

계도기간은 대략 2027년 1월까지이며, 이후 본격 시행됩니다.  
시행령은 형성 중이므로 룰셋은 과기정통부·TTA 공지에 따라 업데이트됩니다.

### 룰셋이 바뀌면 어떻게 알 수 있나요?

`docs/rules/rule_engine_spec_v0.md` 에서 현재 룰셋 버전과 근거 원문을 확인할 수 있습니다.  
변경 시 GitHub Releases 에 반영하므로, 릴리즈를 구독(`Watch > Releases only`)하세요.

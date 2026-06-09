"""KoAI-Verify Python SDK 사용 예제.

이 파일은 koai-verify 패키지의 주요 기능을 보여주는 예제입니다.
실행 전 `pip install koai-verify` 를 먼저 실행하세요.
"""

import glob

from koai_verify import verify
from koai_verify.rules.models import Verdict

# ── 1. 기본 검증 ──────────────────────────────────────────────────────────────
report = verify("path/to/image.jpg")

print(report.verdict)  # COMPLIANT / NON_COMPLIANT / WARNING / UNKNOWN
print(report.to_summary())  # 한국어 요약 출력
print(report.to_json())  # JSON 직렬화

# ── 2. 판정 분기 처리 ─────────────────────────────────────────────────────────
if report.verdict == Verdict.COMPLIANT:
    print("✓ 표시 요건 충족")
elif report.verdict == Verdict.NON_COMPLIANT:
    print("✗ 표시 요건 불충족 — 수정 필요")
    print("위반 룰:", report.triggered_rules)
    print("권고:", report.recommendation)
elif report.verdict == Verdict.WARNING:
    print("△ 경고 — 강건성 생존율이 낮습니다")
else:
    print("? 탐지 불가 (UNKNOWN)")

# ── 3. 탐지 상세 결과 확인 ────────────────────────────────────────────────────
print("C2PA  :", report.detections.get("c2pa"))  # FOUND / NOT_FOUND / UNKNOWN
print("EXIF  :", report.detections.get("exif"))
print("OCR   :", report.detections.get("ocr"))
print("WM    :", report.detections.get("watermark"))

# ── 4. 강건성 배터리 포함 검증 ────────────────────────────────────────────────
report_robust = verify("path/to/image.jpg", robustness=True)

if report_robust.robustness:
    for transform_name, survival_rate in report_robust.robustness.items():
        print(f"  {transform_name}: {survival_rate:.1%} 생존율")

# ── 5. 배치 검증 ─────────────────────────────────────────────────────────────
image_paths = glob.glob("path/to/images/*.jpg")
results = []
for path in image_paths:
    r = verify(path)
    results.append({"path": path, "verdict": r.verdict.value})
    print(f"{path}: {r.verdict.value}")

# NON_COMPLIANT 이미지만 필터링
non_compliant = [r for r in results if r["verdict"] == "NON_COMPLIANT"]
print(f"\n총 {len(image_paths)}개 중 {len(non_compliant)}개 불충족")

#!/usr/bin/env bash
# KoAI-Verify CLI + 향후 호스팅 API curl 사용 예제
#
# 전제조건: pip install koai-verify

set -euo pipefail

IMAGE="path/to/image.jpg"

# ── 1. CLI 기본 검증 (JSON 출력) ──────────────────────────────────────────────
koai-verify "$IMAGE"

# ── 2. 사람이 읽기 좋은 요약 출력 ────────────────────────────────────────────
koai-verify "$IMAGE" --format summary

# ── 3. 강건성 배터리 포함 ──────────────────────────────────────────────────────
koai-verify "$IMAGE" --robustness

# ── 4. jq로 판정 값만 추출 ────────────────────────────────────────────────────
VERDICT=$(koai-verify "$IMAGE" | python3 -c "import sys,json; print(json.load(sys.stdin)['verdict'])")
echo "판정: $VERDICT"

# ── 5. CI/CD 종료 코드 활용 ───────────────────────────────────────────────────
# koai-verify 종료 코드:
#   0 = COMPLIANT
#   1 = NON_COMPLIANT
#   2 = WARNING
#   3 = UNKNOWN
#   10 = 파일 없음 / 처리 오류
if koai-verify "$IMAGE" --format summary; then
  echo "표시 요건 충족 — 배포 계속"
else
  echo "표시 요건 불충족 — 배포 중단" >&2
  exit 1
fi

# ── 6. 디렉터리 내 모든 이미지 일괄 검증 ──────────────────────────────────────
FAIL_COUNT=0
for img in path/to/images/*.jpg; do
  result=$(koai-verify "$img" | python3 -c "import sys,json; print(json.load(sys.stdin)['verdict'])" 2>/dev/null || echo "ERROR")
  echo "$img → $result"
  if [ "$result" = "NON_COMPLIANT" ]; then
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
done

echo "불충족 이미지: $FAIL_COUNT개"
if [ "$FAIL_COUNT" -gt 0 ]; then
  exit 1
fi

# ── 7. 향후 호스팅 API (v0 가동 예정 — W20) ──────────────────────────────────
# curl -X POST https://api.koai-verify.dev/v0/verify \
#   -H "Authorization: Bearer $KOAI_API_KEY" \
#   -F "image=@$IMAGE" \
#   | jq .

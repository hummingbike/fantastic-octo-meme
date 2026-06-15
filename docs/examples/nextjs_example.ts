/**
 * Next.js App Router — KoAI-Verify 통합 예제
 *
 * 파일 위치: app/api/verify/route.ts
 *
 * 설치:
 *   pip install koai-verify   # Python CLI (필수 백엔드)
 *   npm install @koai/verify  # Node.js SDK 래퍼
 *
 * 사용:
 *   curl -X POST http://localhost:3000/api/verify \
 *     -F "image=@/path/to/image.jpg"
 */

import { unlinkSync, writeFileSync } from "fs";
import { tmpdir } from "os";
import { extname, join } from "path";

import { NextRequest, NextResponse } from "next/server";

import { VerifyError, verify } from "@koai/verify";

/** CLI_NOT_FOUND 오류 → 503 Service Unavailable */
const _ERROR_STATUS: Record<string, number> = {
  CLI_NOT_FOUND: 503,
  IMAGE_NOT_FOUND: 400,
  JSON_PARSE_ERROR: 500,
  EXECUTION_ERROR: 500,
};

// ── POST /api/verify ──────────────────────────────────────────────────────────

export async function POST(request: NextRequest): Promise<NextResponse> {
  const formData = await request.formData();
  const file = formData.get("image") as File | null;

  if (!file) {
    return NextResponse.json(
      { error: "image 필드가 없습니다 (multipart/form-data 로 전송하세요)" },
      { status: 400 },
    );
  }

  const ext = extname(file.name || ".jpg") || ".jpg";
  const tmpPath = join(tmpdir(), `koai-verify-${Date.now()}${ext}`);

  try {
    const buffer = Buffer.from(await file.arrayBuffer());
    writeFileSync(tmpPath, buffer);

    const report = verify(tmpPath);

    return NextResponse.json({
      verdict: report.verdict,
      triggered_rules: report.triggered_rules,
      failing_rules: report.failing_rules,
      recommendation: report.recommendation,
      detections: report.detections,
    });
  } catch (e) {
    if (e instanceof VerifyError) {
      const status = _ERROR_STATUS[e.code] ?? 500;
      return NextResponse.json({ error: e.message, code: e.code }, { status });
    }
    return NextResponse.json({ error: "알 수 없는 오류가 발생했습니다" }, { status: 500 });
  } finally {
    try {
      unlinkSync(tmpPath);
    } catch {
      // 임시 파일이 이미 없는 경우 무시
    }
  }
}

// ── 클라이언트 호출 예제 (Client Component) ───────────────────────────────────

/**
 * 클라이언트에서 이미지를 업로드해 판정 결과를 받는 예제.
 *
 * ```tsx
 * const result = await uploadAndVerify(fileInput.files[0]);
 * console.log(result.verdict); // "COMPLIANT" | "NON_COMPLIANT" | ...
 * ```
 */
export async function uploadAndVerify(file: File) {
  const body = new FormData();
  body.append("image", file);

  const res = await fetch("/api/verify", { method: "POST", body });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(`KoAI-Verify 오류 (${res.status}): ${err.error}`);
  }
  return res.json();
}

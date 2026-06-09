/**
 * KoAI-Verify Node.js / TypeScript SDK 사용 예제.
 *
 * 실행 전 `npm install @koai/verify` 를 먼저 실행하세요.
 * TypeScript: ts-node node_example.ts
 * JavaScript: npx tsx node_example.ts
 */

import { verify, Verdict } from "@koai/verify";

// ── 1. 기본 검증 ──────────────────────────────────────────────────────────────
async function basicExample(): Promise<void> {
  const report = await verify("path/to/image.jpg");

  console.log(report.verdict);     // COMPLIANT / NON_COMPLIANT / WARNING / UNKNOWN
  console.log(report.recommendation);
}

// ── 2. 판정 분기 처리 ─────────────────────────────────────────────────────────
async function handleVerdict(): Promise<void> {
  const report = await verify("path/to/image.jpg");

  switch (report.verdict) {
    case Verdict.COMPLIANT:
      console.log("✓ 표시 요건 충족");
      break;
    case Verdict.NON_COMPLIANT:
      console.log("✗ 표시 요건 불충족");
      console.log("위반 룰:", report.triggered_rules);
      console.log("권고:", report.recommendation);
      break;
    case Verdict.WARNING:
      console.log("△ 경고 — 강건성 생존율이 낮습니다");
      break;
    default:
      console.log("? 탐지 불가 (UNKNOWN)");
  }
}

// ── 3. 강건성 배터리 포함 검증 ────────────────────────────────────────────────
async function robustnessExample(): Promise<void> {
  const report = await verify("path/to/image.jpg", { robustness: true });

  if (report.robustness) {
    for (const [transformName, survivalRate] of Object.entries(report.robustness)) {
      console.log(`  ${transformName}: ${(survivalRate as number * 100).toFixed(1)}% 생존율`);
    }
  }
}

// ── 4. 배치 검증 ─────────────────────────────────────────────────────────────
async function batchExample(imagePaths: string[]): Promise<void> {
  const results = await Promise.all(
    imagePaths.map(async (path) => {
      const report = await verify(path);
      return { path, verdict: report.verdict };
    })
  );

  const nonCompliant = results.filter((r) => r.verdict === Verdict.NON_COMPLIANT);
  console.log(`총 ${results.length}개 중 ${nonCompliant.length}개 불충족`);
}

// ── 5. CI/CD 통합 예제 (non-zero exit code on failure) ───────────────────────
async function ciExample(): Promise<void> {
  const report = await verify(process.argv[2] ?? "image.jpg");

  if (report.verdict === Verdict.NON_COMPLIANT) {
    console.error("KoAI-Verify: 표시 요건 불충족 — CI 실패");
    process.exit(1);
  }

  console.log("KoAI-Verify: 표시 요건 충족");
  process.exit(0);
}

// 예제 실행
(async () => {
  await basicExample();
  await handleVerdict();
  await robustnessExample();
})();

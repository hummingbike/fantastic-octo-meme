/**
 * @koai/verify — KoAI-Verify JS/TS SDK
 *
 * 한국 AI 기본법 제31조 표시 의무 검증 Python SDK 래퍼.
 *
 * @example
 * ```typescript
 * import { verify } from '@koai/verify';
 *
 * const report = verify('/path/to/image.jpg');
 * console.log(report.verdict); // 'COMPLIANT' | 'NON_COMPLIANT' | 'WARNING' | 'UNKNOWN'
 * ```
 */

export { verify, parseReport } from "./verify";
export type {
  VerificationReport,
  Detections,
  DetectionResult,
  Verdict,
  VerifyOptions,
  VerifyErrorCode,
} from "./types";
export { VerifyError } from "./types";

/**
 * Python CLI 래퍼 — verify() 핵심 구현.
 *
 * koai-verify CLI 를 subprocess 로 호출하고 JSON 출력을 파싱한다.
 *
 * 환경 변수:
 *   KOAI_VERIFY_CMD  — CLI 실행 명령어 (기본: "koai-verify").
 *                      Python 모듈로 직접 실행하려면
 *                      "python -m koai_verify.cli" 로 설정한다.
 */

import { spawnSync } from "child_process";

import type { VerificationReport, VerifyOptions } from "./types";
import { VerifyError } from "./types";

const _VERDICT_EXIT: Record<number, string> = {
  0: "COMPLIANT",
  1: "NON_COMPLIANT",
  2: "WARNING",
  3: "UNKNOWN",
};

function _getCommand(): string[] {
  const cmd = process.env.KOAI_VERIFY_CMD;
  if (cmd) {
    return cmd.split(/\s+/);
  }
  return ["koai-verify"];
}

/**
 * 이미지를 검증하고 판정 리포트를 반환한다.
 *
 * @param imagePath 검증할 이미지 파일 경로 (절대 또는 상대 경로).
 * @param options   검증 옵션.
 * @returns VerificationReport
 * @throws VerifyError  CLI 실행 실패(파일 없음, 포맷 미지원 등).
 */
export function verify(imagePath: string, options: VerifyOptions = {}): VerificationReport {
  const [bin, ...baseArgs] = _getCommand();
  const args: string[] = [...baseArgs, imagePath, "--format", "json"];
  if (options.robustness) {
    args.push("--robustness");
  }

  const result = spawnSync(bin, args, { encoding: "utf8", env: process.env });

  const exitCode = result.status ?? -1;

  // exit 0–3: 판정 결과 코드 — stdout 에 유효한 JSON 이 있다.
  if (exitCode in _VERDICT_EXIT && result.stdout) {
    try {
      return JSON.parse(result.stdout) as VerificationReport;
    } catch {
      throw new VerifyError(`JSON 파싱 실패: ${result.stdout.slice(0, 200)}`, exitCode);
    }
  }

  // exit 10: 입력 오류 (파일 없음 등)
  const stderr = (result.stderr ?? "").trim();
  throw new VerifyError(`koai-verify 실행 실패 (exit ${exitCode}): ${stderr}`, exitCode);
}

/** JSON 문자열을 VerificationReport 로 파싱한다 (단위 테스트 유틸). */
export function parseReport(json: string): VerificationReport {
  return JSON.parse(json) as VerificationReport;
}

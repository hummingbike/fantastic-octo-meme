/**
 * KoAI-Verify TypeScript 타입 정의.
 *
 * Python SDK VerificationReport JSON 출력과 1:1 대응.
 */

export type DetectionResult = "FOUND" | "NOT_FOUND" | "UNKNOWN";

export type Verdict = "COMPLIANT" | "NON_COMPLIANT" | "WARNING" | "UNKNOWN";

/** 탐지기별 결과 (c2pa / exif / ocr / watermark). */
export interface Detections {
  c2pa: DetectionResult;
  exif: DetectionResult;
  ocr: DetectionResult;
  watermark: DetectionResult;
}

/**
 * koai-verify 판정 리포트.
 *
 * Python VerificationReport.to_json() 출력과 동일한 구조.
 */
export interface VerificationReport {
  /** 원본 이미지 sha256 식별자 ("sha256:<hex>"). */
  image: string;
  /** 판정 결과. */
  verdict: Verdict;
  /** 판정에 기여한 규칙 ID (R-01~R-07). */
  triggered_rules: string[];
  /** 불충족을 유발한 규칙 ID. */
  failing_rules: string[];
  /** 탐지기별 결과. */
  detections: Detections;
  /** 탐지기별 생존율 (0.0–1.0). 측정 안 했으면 빈 객체. */
  robustness: Record<string, number>;
  /** 사람이 읽는 조치 권고문. */
  recommendation: string;
  /** 리포트 생성 시각 (ISO 8601 UTC). */
  timestamp: string;
}

/** verify() 옵션. */
export interface VerifyOptions {
  /** true 이면 변형 배터리를 실행해 생존율을 리포트에 포함한다. */
  robustness?: boolean;
}

/**
 * VerifyError 오류 코드 — 프로그래밍 방식으로 오류 종류를 구분한다.
 *
 * - `CLI_NOT_FOUND`   : koai-verify CLI 를 찾을 수 없음 (설치 미완료).
 * - `IMAGE_NOT_FOUND` : 지정한 이미지 파일이 없음 (exit 10).
 * - `JSON_PARSE_ERROR`: CLI 출력 JSON 파싱 실패 (버그 or 버전 불일치).
 * - `EXECUTION_ERROR` : 그 외 CLI 실행 오류.
 */
export type VerifyErrorCode =
  | "CLI_NOT_FOUND"
  | "IMAGE_NOT_FOUND"
  | "JSON_PARSE_ERROR"
  | "EXECUTION_ERROR";

/** koai-verify 실행 오류. */
export class VerifyError extends Error {
  /**
   * @param message  사람이 읽는 오류 메시지.
   * @param exitCode CLI 종료 코드 (-1 이면 프로세스를 spawn 하지 못한 경우).
   * @param code     오류 종류 코드 (프로그래밍 방식 분기용).
   */
  constructor(
    message: string,
    public readonly exitCode: number,
    public readonly code: VerifyErrorCode = "EXECUTION_ERROR",
  ) {
    super(message);
    this.name = "VerifyError";
  }
}

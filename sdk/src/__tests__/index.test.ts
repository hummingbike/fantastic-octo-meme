/**
 * @koai/verify SDK 단위 테스트.
 *
 * 전략:
 *   - 타입·파싱 테스트: Python 호출 없이 JSON 픽스처로 검증
 *   - 통합 테스트: KOAI_VERIFY_CMD 로 Python 모듈 직접 호출
 *
 * 환경 변수:
 *   KOAI_VERIFY_CMD=python -m koai_verify.cli  (Jest 실행 전 설정 권장)
 */

import * as fs from "fs";
import * as os from "os";
import * as path from "path";

import { parseReport, verify, VerifyError } from "../index";
import type { VerificationReport } from "../index";

// ---------------------------------------------------------------------------
// 픽스처: 판정 리포트 JSON 샘플
// ---------------------------------------------------------------------------

const SAMPLE_REPORT_JSON: string = JSON.stringify({
  image: "sha256:abcdef1234567890",
  verdict: "NON_COMPLIANT",
  triggered_rules: [],
  failing_rules: ["R-05"],
  detections: {
    c2pa: "NOT_FOUND",
    exif: "NOT_FOUND",
    ocr: "NOT_FOUND",
    watermark: "UNKNOWN",
  },
  robustness: {},
  recommendation: "AI 생성 표시를 찾을 수 없습니다.",
  timestamp: "2026-08-17T00:00:00Z",
});

const SAMPLE_COMPLIANT_JSON: string = JSON.stringify({
  image: "sha256:fedcba0987654321",
  verdict: "COMPLIANT",
  triggered_rules: ["R-04"],
  failing_rules: [],
  detections: {
    c2pa: "NOT_FOUND",
    exif: "NOT_FOUND",
    ocr: "FOUND",
    watermark: "UNKNOWN",
  },
  robustness: {},
  recommendation: "가시 라벨이 탐지됐습니다.",
  timestamp: "2026-08-17T00:00:00Z",
});

// ---------------------------------------------------------------------------
// 타입 익스포트 검증
// ---------------------------------------------------------------------------

describe("exports", () => {
  test("verify is exported as function", () => {
    expect(typeof verify).toBe("function");
  });

  test("parseReport is exported as function", () => {
    expect(typeof parseReport).toBe("function");
  });

  test("VerifyError is exported as class", () => {
    expect(typeof VerifyError).toBe("function");
  });
});

// ---------------------------------------------------------------------------
// parseReport() — JSON 파싱 (Python 호출 불필요)
// ---------------------------------------------------------------------------

describe("parseReport()", () => {
  test("parses NON_COMPLIANT report correctly", () => {
    const report: VerificationReport = parseReport(SAMPLE_REPORT_JSON);
    expect(report.verdict).toBe("NON_COMPLIANT");
    expect(report.failing_rules).toContain("R-05");
    expect(report.image).toBe("sha256:abcdef1234567890");
  });

  test("parses COMPLIANT report correctly", () => {
    const report: VerificationReport = parseReport(SAMPLE_COMPLIANT_JSON);
    expect(report.verdict).toBe("COMPLIANT");
    expect(report.triggered_rules).toContain("R-04");
  });

  test("report has all required fields", () => {
    const report: VerificationReport = parseReport(SAMPLE_REPORT_JSON);
    expect(report).toHaveProperty("image");
    expect(report).toHaveProperty("verdict");
    expect(report).toHaveProperty("triggered_rules");
    expect(report).toHaveProperty("failing_rules");
    expect(report).toHaveProperty("detections");
    expect(report).toHaveProperty("robustness");
    expect(report).toHaveProperty("recommendation");
    expect(report).toHaveProperty("timestamp");
  });

  test("detections has four detector keys", () => {
    const report: VerificationReport = parseReport(SAMPLE_REPORT_JSON);
    expect(Object.keys(report.detections)).toEqual(
      expect.arrayContaining(["c2pa", "exif", "ocr", "watermark"]),
    );
  });

  test("robustness is empty object when not measured", () => {
    const report: VerificationReport = parseReport(SAMPLE_REPORT_JSON);
    expect(report.robustness).toEqual({});
  });

  test("timestamp is ISO 8601 string", () => {
    const report: VerificationReport = parseReport(SAMPLE_REPORT_JSON);
    expect(report.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/);
  });

  test("image starts with sha256:", () => {
    const report: VerificationReport = parseReport(SAMPLE_REPORT_JSON);
    expect(report.image).toMatch(/^sha256:/);
  });

  test("throws SyntaxError on invalid JSON", () => {
    expect(() => parseReport("not json")).toThrow(SyntaxError);
  });
});

// ---------------------------------------------------------------------------
// VerifyError
// ---------------------------------------------------------------------------

describe("VerifyError", () => {
  test("is instance of Error", () => {
    const err = new VerifyError("test", 10);
    expect(err).toBeInstanceOf(Error);
  });

  test("has name VerifyError", () => {
    const err = new VerifyError("test", 10);
    expect(err.name).toBe("VerifyError");
  });

  test("stores exitCode", () => {
    const err = new VerifyError("test error", 10);
    expect(err.exitCode).toBe(10);
  });

  test("message is accessible", () => {
    const err = new VerifyError("some message", 1);
    expect(err.message).toBe("some message");
  });
});

// ---------------------------------------------------------------------------
// verify() — Python 호출 통합 테스트
// (KOAI_VERIFY_CMD 가 설정된 경우에만 실행)
// ---------------------------------------------------------------------------

const SKIP_INTEGRATION = !process.env.KOAI_VERIFY_CMD;

describe("verify() integration", () => {
  let tmpDir: string;
  let plainJpeg: string;

  beforeAll(() => {
    if (SKIP_INTEGRATION) return;
    // koai_verify 가 sys.path 에 없을 경우를 위해 프로젝트 루트를 PYTHONPATH 에 추가
    const projectRoot = path.resolve(__dirname, "../../..");
    process.env.PYTHONPATH = process.env.PYTHONPATH
      ? `${projectRoot}${path.delimiter}${process.env.PYTHONPATH}`
      : projectRoot;

    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "koai-test-"));
    const { execSync } = require("child_process");
    plainJpeg = path.join(tmpDir, "plain.jpg");
    execSync(
      `python -c "from PIL import Image; p=Image.new('RGB',(32,32),(100,150,200)); p.save('${plainJpeg}','JPEG')"`,
      { env: process.env },
    );
  });

  afterAll(() => {
    if (tmpDir) {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });

  const maybeTest = SKIP_INTEGRATION ? test.skip : test;

  maybeTest("plain image returns VerificationReport", () => {
    const report = verify(plainJpeg);
    expect(report).toHaveProperty("verdict");
    expect(report).toHaveProperty("detections");
    expect(["COMPLIANT", "NON_COMPLIANT", "WARNING", "UNKNOWN"]).toContain(report.verdict);
  });

  maybeTest("plain image verdict is NON_COMPLIANT", () => {
    const report = verify(plainJpeg);
    expect(report.verdict).toBe("NON_COMPLIANT");
  });

  maybeTest("image field starts with sha256:", () => {
    const report = verify(plainJpeg);
    expect(report.image).toMatch(/^sha256:/);
  });

  maybeTest("detections has four keys", () => {
    const report = verify(plainJpeg);
    expect(new Set(Object.keys(report.detections))).toEqual(new Set(["c2pa", "exif", "ocr", "watermark"]));
  });

  maybeTest("missing file throws VerifyError", () => {
    expect(() => verify(path.join(tmpDir, "no_such_file.jpg"))).toThrow(VerifyError);
  });
});

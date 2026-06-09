/** @type {import('ts-jest').JestConfigWithTsJest} */
module.exports = {
  preset: "ts-jest",
  testEnvironment: "node",
  testMatch: ["**/src/__tests__/**/*.test.ts"],
  transform: {
    "^.+\\.tsx?$": ["ts-jest", { tsconfig: "tsconfig.json" }],
  },
  // koai_verify Python 패키지가 설치되지 않은 경우 프로젝트 루트를 PYTHONPATH 에 추가
  setupFiles: ["./jest.setup.js"],
};

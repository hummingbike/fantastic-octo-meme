const path = require("path");

// koai_verify Python 패키지가 시스템에 설치되지 않은 경우를 위해
// 프로젝트 루트를 PYTHONPATH 에 추가한다.
const projectRoot = path.resolve(__dirname, "..");
if (!process.env.PYTHONPATH || !process.env.PYTHONPATH.includes(projectRoot)) {
  process.env.PYTHONPATH = process.env.PYTHONPATH
    ? `${projectRoot}${path.delimiter}${process.env.PYTHONPATH}`
    : projectRoot;
}

"""W16 강건성 벤치마크 실행 스크립트.

사용법:
    python scripts/run_benchmark.py
    python scripts/run_benchmark.py --images tests/fixtures/samples/midjourney/midjourney_01.jpg
    python scripts/run_benchmark.py --output benchmarks/results/

산출물:
    benchmarks/results/survival_matrix_v1.json  — 포맷 × 변형 생존율 매트릭스
    benchmarks/results/survival_summary_v1.md   — 사람 읽기용 요약 마크다운
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from benchmarks.matrix import (  # noqa: E402
    DetectionFormat,
    SurvivalMatrix,
    empty_matrix,
    evaluate_robustness,
    format_survival_summary,
)
from benchmarks.transform_spec import TRANSFORM_BATTERY  # noqa: E402
from koai_verify.detectors.c2pa_detector import C2PADetector  # noqa: E402
from koai_verify.detectors.exif_detector import EXIFDetector  # noqa: E402
from koai_verify.detectors.ocr_detector import OCRDetector  # noqa: E402
from koai_verify.detectors.result import DetectionResult  # noqa: E402
from koai_verify.robustness.harness import run_battery  # noqa: E402

DETECTOR_FORMAT_MAP = {
    "c2pa": DetectionFormat.C2PA,
    "exif": DetectionFormat.EXIF,
    "ocr": DetectionFormat.VISIBLE_LABEL,
}

DEFAULT_IMAGES = [
    ROOT / "tests/fixtures/c2pa/c2pa_test_C.jpg",
    ROOT / "tests/fixtures/ocr/ocr_aigc.jpg",
    ROOT / "tests/fixtures/ocr/ocr_en_label.jpg",
    ROOT / "tests/fixtures/ocr/ocr_ko_ascii_label.jpg",
    ROOT / "tests/fixtures/ocr/ocr_made_with_ai.jpg",
    ROOT / "tests/fixtures/ocr/ocr_no_label.jpg",
    ROOT / "tests/fixtures/samples/midjourney/midjourney_01.jpg",
    ROOT / "tests/fixtures/samples/stable_diffusion/stable_diffusion_01.jpg",
    ROOT / "tests/fixtures/samples/firefly/firefly_01.jpg",
]


def _build_detectors():
    return {
        "c2pa": C2PADetector(),
        "exif": EXIFDetector(),
        "ocr": OCRDetector(),
    }


def run_full_matrix(image_paths: list[Path]) -> tuple[SurvivalMatrix, dict]:
    """모든 이미지에 대해 탐지기 × 변형 배터리를 실행하고 매트릭스를 채운다.

    이미지가 여러 개일 때는 포맷별로 생존율을 집계(평균)한다.
    원본 탐지가 FOUND 인 이미지만 측정에 포함한다.
    """
    detectors = _build_detectors()
    matrix = empty_matrix()

    # 포맷별 변형별 (생존 횟수, 측정 횟수) 누적
    accum: dict[str, dict[str, list[bool]]] = {
        fmt.value: {spec.label(): [] for spec in TRANSFORM_BATTERY}
        for fmt in DetectionFormat
        if fmt != DetectionFormat.OPEN_WATERMARK
    }

    image_meta: list[dict] = []
    for img_path in image_paths:
        if not img_path.exists():
            print(f"  [SKIP] 파일 없음: {img_path}")
            continue
        image_bytes = img_path.read_bytes()
        print(f"  이미지: {img_path.name}")

        for det_name, detector in detectors.items():
            fmt_key = det_name  # c2pa / exif / ocr
            report = run_battery(image_bytes, detector)
            orig = report.original_result
            status = "FOUND" if orig == DetectionResult.FOUND else orig.value
            print(f"    {det_name:6s} 원본={status}  ", end="")
            if orig == DetectionResult.FOUND:
                rate = report.survival_rate()
                print(f"생존율={rate:.1%}  생존={len(report.surviving())}  소실={len(report.broken())}")
            else:
                print("측정 불가 (원본 탐지 안 됨)")

            for entry in report.entries:
                if entry.survived is not None:
                    accum[fmt_key][entry.transform_label].append(entry.survived)

        image_meta.append(
            {
                "path": str(img_path.relative_to(ROOT)),
                "detections": {
                    det_name: detector.detect_safe(img_path.read_bytes()).result.value
                    for det_name, detector in detectors.items()
                },
            }
        )

    # 누적 → 평균 생존율 → matrix 채우기
    for fmt_key, transforms in accum.items():
        fmt_enum = DetectionFormat(fmt_key)
        for label, results in transforms.items():
            if results:
                rate = sum(results) / len(results)
                matrix.set_rate(fmt_enum, label, rate)

    # OPEN_WATERMARK 는 항상 UNKNOWN (측정 불가)
    for spec in TRANSFORM_BATTERY:
        matrix.set_rate(DetectionFormat.OPEN_WATERMARK, spec.label(), None)

    return matrix, {"images": image_meta}


def build_summary_markdown(
    matrix: SurvivalMatrix,
    meta: dict,
    image_paths: list[Path],
) -> str:
    summary = format_survival_summary(matrix)
    r06 = evaluate_robustness(matrix)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        "# KoAI-Verify 강건성 벤치마크 결과 v1",
        "",
        f"> 생성일: {now}  ",
        f"> 픽스처: {len([p for p in image_paths if p.exists()])}개 이미지 (합성 픽스처 기반)  ",
        f"> 변형: {len(TRANSFORM_BATTERY)}종 / 탐지 포맷: 4종 (C2PA·EXIF·가시라벨·오픈워터마크)  ",
        "> **주의**: 이 결과는 합성 테스트 픽스처 기반입니다. 실제 AI 생성 이미지 결과와 다를 수 있습니다.",
        "",
        "---",
        "",
        "## 핵심 요약",
        "",
        "| 탐지 포맷 | 평균 생존율 | 비고 |",
        "|---|---|---|",
    ]

    format_labels = {
        "c2pa": "C2PA 매니페스트",
        "exif": "EXIF AI 플래그",
        "visible_label": "가시 라벨 (OCR)",
        "open_watermark": "오픈 워터마크",
    }
    for fmt_key, label in format_labels.items():
        rates = [v for v in (summary.get(fmt_key) or {}).values() if v is not None]
        if not rates:
            avg = "측정 불가"
            note = "원본 탐지 FOUND 이미지 없음" if fmt_key != "open_watermark" else "항상 UNKNOWN"
        else:
            avg_val = sum(rates) / len(rates)
            avg = f"{avg_val:.1%}"
            note = "R-06 경고 없음" if avg_val >= 0.8 else "⚠️ R-06 경고 트리거"
        lines.append(f"| {label} | {avg} | {note} |")

    lines += [
        "",
        f"**R-06 평가**: 임계치 {r06['threshold']:.0%} — "
        f"측정 {r06['total_measured']}셀 중 임계치 미달 {r06['failing_count']}셀",
        "",
        "---",
        "",
        "## SNS 재인코딩 생존율 (핵심)",
        "",
        "| 플랫폼 | C2PA | EXIF | 가시라벨 | 비고 |",
        "|---|---|---|---|---|",
    ]

    sns_labels = {
        "sns_instagram": "Instagram",
        "sns_twitter": "Twitter/X",
        "sns_kakaotalk_chat": "KakaoTalk 채팅",
        "sns_kakaotalk_profile": "KakaoTalk 프로필",
    }
    for key, name in sns_labels.items():
        c2pa_r = (summary.get("c2pa") or {}).get(key)
        exif_r = (summary.get("exif") or {}).get(key)
        ocr_r = (summary.get("visible_label") or {}).get(key)

        def fmt_rate(r):
            return f"{r:.1%}" if r is not None else "N/A"

        note = "⚠️ 완전 소거 위험" if (c2pa_r == 0.0 or exif_r == 0.0) else ""
        lines.append(f"| {name} | {fmt_rate(c2pa_r)} | {fmt_rate(exif_r)} | {fmt_rate(ocr_r)} | {note} |")

    lines += [
        "",
        "---",
        "",
        "## 변형별 상세 생존율 — EXIF AI 플래그",
        "",
        "| 변형 | 생존율 |",
        "|---|---|",
    ]
    exif_summary = summary.get("exif") or {}
    for spec in TRANSFORM_BATTERY:
        rate = exif_summary.get(spec.label())
        rate_str = f"{rate:.1%}" if rate is not None else "N/A"
        lines.append(f"| {spec.label()} | {rate_str} |")

    lines += [
        "",
        "---",
        "",
        "## 변형별 상세 생존율 — 가시 라벨 (OCR)",
        "",
        "| 변형 | 생존율 |",
        "|---|---|",
    ]
    ocr_summary = summary.get("visible_label") or {}
    for spec in TRANSFORM_BATTERY:
        rate = ocr_summary.get(spec.label())
        rate_str = f"{rate:.1%}" if rate is not None else "N/A"
        lines.append(f"| {spec.label()} | {rate_str} |")

    lines += [
        "",
        "---",
        "",
        "## 분석 이미지 목록",
        "",
        "| 이미지 | C2PA | EXIF | OCR |",
        "|---|---|---|---|",
    ]
    for img_info in meta.get("images", []):
        d = img_info.get("detections", {})
        name = Path(img_info["path"]).name
        lines.append(f"| {name} | {d.get('c2pa','?')} | {d.get('exif','?')} | {d.get('ocr','?')} |")

    lines += [
        "",
        "---",
        "",
        "## 방법론",
        "",
        "- **변형 배터리**: 20종 (`benchmarks/transform_spec.py` `TRANSFORM_BATTERY`)",
        "- **탐지 포맷**: C2PA (c2pa-python), EXIF (piexif/Pillow), 가시라벨 (OCR 패턴), 오픈워터마크 (UNKNOWN)",
        "- **생존 기준**: 원본 FOUND → 변형 후 FOUND 이면 생존",
        "- **픽스처**: 합성 JPEG (실제 AI 도구 출력 아님 — 실측치는 gap_report_v1.md 참조)",
        "- **R-06 임계치**: 80% — 미달 시 WARNING 판정",
        "",
        "자세한 프로토콜: [benchmarks/protocol_v1.md](../protocol_v1.md)",
    ]

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KoAI-Verify 강건성 벤치마크 실행")
    parser.add_argument(
        "--images",
        nargs="*",
        help="검증할 이미지 경로 목록 (기본: 내장 픽스처)",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "benchmarks/results"),
        help="결과 출력 디렉터리 (기본: benchmarks/results/)",
    )
    args = parser.parse_args(argv)

    image_paths = [Path(p) for p in args.images] if args.images else DEFAULT_IMAGES
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=== KoAI-Verify 강건성 벤치마크 v1 ===")
    print(f"이미지 {len(image_paths)}개  변형 {len(TRANSFORM_BATTERY)}종\n")

    matrix, meta = run_full_matrix(image_paths)

    # JSON 저장
    json_path = output_dir / "survival_matrix_v1.json"
    result_data = {
        "version": "1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fixture_note": "합성 테스트 픽스처 기반 — 실측치는 gap_report_v1.md 참조",
        "transform_count": len(TRANSFORM_BATTERY),
        "detector_formats": ["c2pa", "exif", "visible_label", "open_watermark"],
        "r06_threshold": 0.8,
        "matrix": matrix.to_dict(),
        "r06_evaluation": evaluate_robustness(matrix),
        "images": meta["images"],
    }
    json_path.write_text(json.dumps(result_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[저장] {json_path}")

    # Markdown 저장
    md_path = output_dir / "survival_summary_v1.md"
    md_content = build_summary_markdown(matrix, meta, image_paths)
    md_path.write_text(md_content, encoding="utf-8")
    print(f"[저장] {md_path}")

    # R-06 요약 출력
    r06 = evaluate_robustness(matrix)
    print(f"\nR-06 평가: 임계치={r06['threshold']:.0%}  측정={r06['total_measured']}셀  미달={r06['failing_count']}셀")
    if r06["r06_triggered"]:
        print("⚠️  R-06 WARNING 트리거됨")
    else:
        print("✓  R-06 통과")

    return 0


if __name__ == "__main__":
    sys.exit(main())

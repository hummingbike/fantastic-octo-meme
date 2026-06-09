"""W12 — 웹 플레이그라운드.

koai-verify SDK 를 드래그&드롭 웹 UI 로 체험한다.

실행:
  # Gradio 설치 후 실행
  pip install koai-verify[playground]
  python playground/app.py

  # 또는 dev 환경에서
  poetry run python playground/app.py

의존성:
  Gradio (선택): pip install gradio
  Gradio 없이 import 해도 process_image() 함수는 사용 가능.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from koai_verify import verify
from koai_verify.pipeline import ImageLoadError


def process_image(image_path: Optional[str]) -> tuple[str, str]:
    """이미지 파일을 검증하고 (JSON 리포트, 사람 읽기용 요약) 튜플을 반환한다.

    Gradio Interface 핸들러 및 단위 테스트에서 직접 호출한다.

    Args:
        image_path: 검증할 이미지 파일 경로 (Gradio 에서 filepath 타입으로 전달).

    Returns:
        (json_report, summary) 튜플.
    """
    if image_path is None or not Path(image_path).exists():
        empty = '{"error": "이미지를 선택해주세요"}'
        return empty, "이미지를 선택해주세요."

    try:
        report = verify(image_path)
    except ImageLoadError as e:
        err = f'{{"error": "{e}"}}'
        return err, f"입력 오류: {e}"

    return report.to_json(), report.to_summary()


def _build_demo():
    """Gradio Interface 를 생성해 반환한다. Gradio 미설치 시 None."""
    try:
        import gradio as gr
    except ImportError:
        return None

    demo = gr.Interface(
        fn=process_image,
        inputs=gr.Image(type="filepath", label="이미지 파일 (드래그&드롭 또는 클릭)"),
        outputs=[
            gr.Textbox(label="JSON 판정 리포트", lines=20, max_lines=30),
            gr.Textbox(label="사람 읽기용 요약", lines=10, max_lines=20),
        ],
        title="KoAI-Verify 웹 플레이그라운드",
        description=(
            "**한국 AI 기본법 제31조 표시 의무 검증**\n\n"
            "이미지를 업로드하면 C2PA 매니페스트, EXIF AI 메타데이터, 가시 라벨, "
            "워터마크를 탐지하고 법적 컴플라이언스 판정 리포트를 생성합니다."
        ),
        examples=None,
        allow_flagging="never",
    )
    return demo


demo = _build_demo()


if __name__ == "__main__":
    if demo is None:
        raise SystemExit(
            "Gradio 가 설치되지 않았습니다.\n" "  pip install koai-verify[playground]  또는\n" "  pip install gradio"
        )
    demo.launch()

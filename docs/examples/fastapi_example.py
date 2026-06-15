"""FastAPI + KoAI-Verify 통합 예제.

설치:
    pip install koai-verify fastapi uvicorn python-multipart

실행:
    uvicorn fastapi_example:app --reload

엔드포인트:
    POST /verify  — 이미지 파일 업로드 → 제31조 판정 리포트 반환
"""

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from koai_verify import (
    ImageCorruptedError,
    ImageNotFoundError,
    ImageTooLargeError,
    UnsupportedFormatError,
    UrlNotAllowedError,
    verify,
)

app = FastAPI(
    title="KoAI-Verify API",
    version="0.1.0",
    description="한국 AI 기본법 제31조 표시 의무 검증 서비스",
)


@app.post(
    "/verify",
    summary="AI 생성 이미지 검증",
    description="이미지를 업로드해 한국 AI 기본법 제31조 표시 요건 충족 여부를 판정합니다.",
)
async def verify_image(image: UploadFile = File(...)) -> JSONResponse:
    """AI 생성 이미지의 제31조 표시 요건 충족 여부를 판정하고 결과를 반환한다."""
    suffix = Path(image.filename or "image.jpg").suffix or ".jpg"
    tmp_path: str | None = None

    try:
        content = await image.read()

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        report = verify(tmp_path)

        return JSONResponse(
            content={
                "verdict": report.verdict,
                "triggered_rules": report.triggered_rules,
                "failing_rules": report.failing_rules,
                "recommendation": report.recommendation,
                "detections": report.detections,
            }
        )

    except (UnsupportedFormatError, ImageCorruptedError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except ImageTooLargeError as e:
        raise HTTPException(status_code=413, detail=str(e)) from e
    except (ImageNotFoundError, UrlNotAllowedError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


# ── 배치 검증 엔드포인트 ──────────────────────────────────────────────────────


@app.post(
    "/verify/batch",
    summary="AI 생성 이미지 배치 검증",
    description="여러 이미지를 한 번에 업로드해 각각의 판정 결과를 반환합니다.",
)
async def verify_batch(images: list[UploadFile] = File(...)) -> JSONResponse:
    """여러 이미지를 순서대로 검증하고 결과 리스트를 반환한다."""
    results = []

    for image in images:
        suffix = Path(image.filename or "image.jpg").suffix or ".jpg"
        tmp_path: str | None = None

        try:
            content = await image.read()

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            report = verify(tmp_path)
            results.append(
                {
                    "filename": image.filename,
                    "verdict": report.verdict,
                    "failing_rules": report.failing_rules,
                    "recommendation": report.recommendation,
                }
            )

        except (UnsupportedFormatError, ImageCorruptedError, ImageTooLargeError) as e:
            results.append({"filename": image.filename, "error": str(e)})

        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)

    non_compliant = [r for r in results if r.get("verdict") == "NON_COMPLIANT"]

    return JSONResponse(
        content={
            "total": len(results),
            "non_compliant_count": len(non_compliant),
            "results": results,
        }
    )

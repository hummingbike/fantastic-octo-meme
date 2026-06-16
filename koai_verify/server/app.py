"""W20 — 호스팅 검증 API v0.

엔드포인트:
  POST /v0/verify   — 이미지 파일 업로드 → 판정 리포트 반환
  GET  /v0/health   — 서버 상태 확인
  GET  /v0/usage    — 사용량 통계 (API 키 필요)

실행:
  uvicorn koai_verify.server.app:app --reload
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from koai_verify.api import verify
from koai_verify.pipeline import ImageLoadError
from koai_verify.server.auth import require_api_key
from koai_verify.server.usage import UsageTracker, get_tracker

_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

app = FastAPI(
    title="KoAI-Verify API",
    version="0.1.0",
    description="한국 AI 기본법 제31조 표시 의무 검증 REST API",
)


@app.get("/v0/health")
async def health() -> dict:
    """서버 상태 확인. 인증 불필요."""
    return {"status": "ok", "version": "0.1.0"}


@app.post("/v0/verify")
async def verify_image(
    file: Annotated[UploadFile, File(description="검증할 이미지 파일 (JPEG/PNG/WebP)")],
    robustness: Annotated[bool, Form()] = False,
    api_key: str = Depends(require_api_key),
    tracker: UsageTracker = Depends(get_tracker),
) -> JSONResponse:
    """이미지를 업로드해 한국 AI 표시 의무 판정 리포트를 반환한다.

    - **file**: JPEG / PNG / WebP 이미지 (최대 50 MB)
    - **robustness**: true 이면 변형 배터리 생존율을 포함한다 (처리 시간 ↑)

    응답 필드:
    - `verdict`: COMPLIANT / NON_COMPLIANT / WARNING / UNKNOWN
    - `triggered_rules`: 판정에 기여한 규칙 ID (R-01~R-07)
    - `detections`: 탐지기별 결과
    - `robustness`: 탐지기별 생존율 (robustness=true 일 때만)
    - `recommendation`: 조치 권고문
    """
    content = await file.read()
    size = len(content)

    if size == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="빈 파일입니다.")
    if size > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"파일이 너무 큽니다 (최대 50 MB, 받은 크기: {size} bytes).",
        )

    t0 = time.monotonic()
    tmp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=_safe_suffix(file.filename)) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        report = verify(tmp_path, robustness=robustness)
    except ImageLoadError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    duration_ms = (time.monotonic() - t0) * 1000
    tracker.record(
        image_size_bytes=size,
        verdict=report.verdict,
        api_key=api_key,
        duration_ms=duration_ms,
    )

    return JSONResponse(content=report.to_dict())


@app.get("/v0/usage")
async def usage_stats(
    api_key: str = Depends(require_api_key),
    tracker: UsageTracker = Depends(get_tracker),
) -> dict:
    """사용량 통계를 반환한다. API 키 인증 필요."""
    stats = tracker.get_stats()
    return stats.to_dict()


def _safe_suffix(filename: Optional[str]) -> str:
    if not filename:
        return ".bin"
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ".bin"
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    return suffix if suffix in allowed else ".bin"

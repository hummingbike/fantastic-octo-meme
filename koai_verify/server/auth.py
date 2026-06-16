"""W20 — API 키 인증 모듈.

인증 방식:
  - `X-API-Key` 헤더에 유효한 키가 있으면 통과.
  - 환경변수 `KOAI_DEV_MODE=true` 이면 키 검사를 건너뛴다 (개발 모드).
  - 환경변수 `KOAI_API_KEYS` (콤마 구분)로 허용 키 목록 지정.
  - 설정 파일 `~/.koai/api_keys.json`의 `["key1", "key2"]` 목록도 허용.

셀프서브 키 발급:
  - `KOAI_API_KEYS` 에 원하는 키를 직접 추가하거나
  - `~/.koai/api_keys.json`를 편집한다.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import Header, HTTPException, status

_CONFIG_PATH = Path.home() / ".koai" / "api_keys.json"


def _load_config_keys() -> set[str]:
    if not _CONFIG_PATH.exists():
        return set()
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {str(k) for k in data if k}
    except (OSError, json.JSONDecodeError):
        pass
    return set()


def _load_env_keys() -> set[str]:
    raw = os.environ.get("KOAI_API_KEYS", "")
    return {k.strip() for k in raw.split(",") if k.strip()}


def is_dev_mode() -> bool:
    return os.environ.get("KOAI_DEV_MODE", "").lower() in ("1", "true", "yes")


def get_valid_keys() -> set[str]:
    return _load_env_keys() | _load_config_keys()


async def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> str:
    """FastAPI 의존성: 유효한 API 키를 요구하거나 개발 모드를 허용한다.

    Returns:
        인증된 API 키 문자열 (개발 모드면 "__dev__").

    Raises:
        HTTPException 401: 키 없음.
        HTTPException 403: 키 유효하지 않음.
    """
    if is_dev_mode():
        return "__dev__"

    valid_keys = get_valid_keys()

    if not valid_keys:
        # 키가 아무것도 등록되지 않았으면 dev 모드처럼 통과 (초기 설정 편의)
        return x_api_key or "__unset__"

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key 헤더가 필요합니다.",
        )

    if x_api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="유효하지 않은 API 키입니다.",
        )

    return x_api_key

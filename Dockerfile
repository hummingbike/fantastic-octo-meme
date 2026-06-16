FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 (Pillow, c2pa-python 빌드에 필요)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# 의존성 설치 (캐시 레이어 분리)
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    "Pillow>=10.0" \
    "piexif>=1.1" \
    "click>=8.0" \
    "fastapi>=0.111" \
    "uvicorn[standard]>=0.29" \
    "python-multipart>=0.0.9" \
    "c2pa-python>=0.32" \
    || true

# 소스 복사
COPY koai_verify/ ./koai_verify/

# 비루트 사용자로 실행
RUN useradd -m -u 1000 koai && chown -R koai:koai /app
USER koai

EXPOSE 8000

# 개발 모드 기본값 off — 운영 배포 시 KOAI_API_KEYS 환경변수 설정 필요
ENV KOAI_DEV_MODE=false

CMD ["uvicorn", "koai_verify.server.app:app", "--host", "0.0.0.0", "--port", "8000"]

# FaceTrace backend (FastAPI) image.
#
# Build from the repository root:
#   docker build -t facetrace-backend .
# Run with the backend environment variables (see README):
#   docker run --env-file backend/.env -p 8000:8000 facetrace-backend
#
# Face detection and matching run on AWS Rekognition, so every dependency in
# backend/requirements.txt ships as a prebuilt wheel: no compilers, OpenCV or
# dlib system libraries are needed in either stage.

# ==================== Stage 1: dependencies ====================
FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN uv venv /opt/venv

# Copy only the requirements first so this layer is cached across code changes.
COPY backend/requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python /opt/venv/bin/python -r /tmp/requirements.txt

# ==================== Stage 2: runtime ====================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    WEB_CONCURRENCY=4

RUN groupadd --system --gid 1000 appuser \
    && useradd --system --uid 1000 --gid appuser --no-create-home appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY --chown=appuser:appuser backend/app /app/app
COPY --chown=appuser:appuser backend/alembic /app/alembic
COPY --chown=appuser:appuser backend/alembic.ini /app/alembic.ini

USER appuser

EXPOSE 8000

# Uses the standard library instead of curl so no extra packages are needed.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"]

# Uvicorn takes its worker count from $WEB_CONCURRENCY (default 4 above).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

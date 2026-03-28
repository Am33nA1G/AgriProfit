# =============================================================================
# AgriProfit Backend — Multi-stage Dockerfile
# Build context: repo root (not ./backend)
# docker-compose: context: . | dockerfile: backend/Dockerfile
# =============================================================================
# NOTE: ML artifacts (ml/artifacts/ ~1 GB) and agmarknet_daily_10yr.parquet
# (~162 MB) are baked into this image. Migrate to S3 + EFS before scaling.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — install Python deps (needs gcc for some native wheels)
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: Runtime — lean image, no build tools
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Runtime lib for psycopg (postgres client)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# ---------------------------------------------------------------------------
# Directory layout mirrors the dev repo so REPO_ROOT resolves correctly.
# In code: REPO_ROOT = Path(__file__).parent × 4 from backend/app/ml/*.py
# → /repo/backend/app/ml/loader.py → 4 parents up → /repo  ✓
# ---------------------------------------------------------------------------
WORKDIR /repo/backend

# Backend application code
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini .

# ML artifacts (referenced via REPO_ROOT / "ml" / "artifacts")
COPY ml /repo/ml

# Historical price dataset (referenced via REPO_ROOT / "agmarknet_daily_10yr.parquet")
COPY agmarknet_daily_10yr.parquet /repo/

# Uploads directory (user-uploaded files — mount as external volume in prod)
RUN mkdir -p /repo/backend/uploads/images

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# AgentLens self-host image — air-gap friendly.
# Python 3.13 slim base; no build-tools needed (pure-Python deps).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first (better layer caching).
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy application code.
COPY api ./api
COPY pipeline ./pipeline
COPY storage ./storage
COPY evaluation ./evaluation
COPY agentlens ./agentlens
COPY dashboard ./dashboard

# Persistent SQLite volume mount target.
RUN mkdir -p /data
ENV DATABASE_URL=sqlite+aiosqlite:////data/agentlens.db

# NOTE: AGENTLENS_AIRGAP is intentionally NOT set here. Self-host deployments
# (docker-compose.yml, scripts/install.sh, CI smoke test) set it explicitly at
# `docker run -e AGENTLENS_AIRGAP=1`. The hosted production (Railway) deploys
# via Procfile + Nixpacks, not this Dockerfile, but if that ever changes we
# don't want this image to silently disable the LLM judge / Stripe / Resend.

EXPOSE 8000

# uvicorn workers=1 keeps SQLite simple; raise only with Postgres backend.
# Shell-form CMD so ${PORT} expands at runtime:
#   - Railway sets $PORT dynamically → bind to that
#   - Self-host (docker-compose) leaves $PORT unset → fall back to 8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

FROM node:24-bookworm-slim AS frontend-builder
WORKDIR /workspace/app/frontend
COPY app/frontend/package.json app/frontend/package-lock.json ./
RUN npm ci
COPY app/frontend/ ./
RUN npm run build

FROM python:3.10-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/root/.local/bin:${PATH}"

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY app/backend/pyproject.toml app/backend/uv.lock ./app/backend/
RUN cd app/backend && uv sync --frozen --no-dev

COPY app/backend ./app/backend
COPY --from=frontend-builder /workspace/app/frontend/dist ./app/frontend/dist

ENV FRONTEND_DIST=/workspace/app/frontend/dist \
    MODEL_ROOT=/workspace/runtime/models \
    OUTPUT_ROOT=/workspace/runtime/output \
    JOBS_ROOT=/workspace/runtime/data/jobs \
    LOGS_ROOT=/workspace/runtime/logs \
    OFFLINE_MODE=true \
    DEMO_MODE=true

EXPOSE 8000

CMD ["sh", "-c", "cd /workspace/app/backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]

# syntax=docker/dockerfile:1.7
FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/root/.local/bin:${PATH}"

WORKDIR /workspace/app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY app/backend ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --index-url https://download.pytorch.org/whl/cpu "torch==2.11.0+cpu"
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system .

ENV MODEL_ROOT=/workspace/runtime/models \
    OUTPUT_ROOT=/workspace/runtime/output \
    JOBS_ROOT=/workspace/runtime/data/jobs \
    LOGS_ROOT=/workspace/runtime/logs \
    OFFLINE_MODE=true \
    DEMO_MODE=true \
    ENABLE_QWEN=false \
    QWEN_ENABLED_IN_UI=false

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

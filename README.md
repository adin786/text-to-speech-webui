# Text to Speech WebUI

Local-first text-to-speech web application with a React frontend and FastAPI backend.

## Stack

- Frontend: React + Vite
- Backend: FastAPI + Pydantic
- Python package management: `uv`
- Audio encoding: `ffmpeg`

## Local development

Backend:

```bash
cd app/backend
uv sync --all-extras
uv run uvicorn app.main:app --reload
```

Frontend:

```bash
cd app/frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

## Tests

```bash
cd app/backend
uv run pytest
```

## Kokoro setup

Download the real Kokoro model files and the required English spaCy model:

```bash
cd app/backend
UV_CACHE_DIR=/tmp/uv-cache uv run python ../../scripts/preload_models.py --root ../../runtime/models --model kokoro
```

After those files are present, the backend will automatically use real Kokoro inference for the `kokoro` model. It only falls back to demo synthesis when Kokoro assets are missing and `DEMO_MODE=true`.

## Demo offline prep

```bash
uv run python scripts/preload_models.py --demo --model kokoro --model qwen3_0_6b
```

This writes local model placeholder manifests under `runtime/models`. Replace those directories with real model weights when wiring the actual Kokoro and Qwen runtimes.

## Docker

```bash
docker compose up --build
```

This starts:

- `frontend`: nginx serving the built React app on `http://127.0.0.1:3000`
- `backend`: FastAPI on the internal Compose network, proxied by the frontend container at `/api`

The default Compose stack is CPU-first and keeps Qwen disabled. Runtime data is mounted from the local `runtime/` directory.
The backend Dockerfiles use BuildKit cache mounts for `uv`, so repeated image builds can reuse downloaded Python packages.

## Optional GPU Scaffold

There is also an optional override file and separate backend Dockerfile reserved for a future GPU-oriented backend path:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

That path is not the default deployment target and is intentionally separate from the main Kokoro CPU stack.

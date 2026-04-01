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
uv python install 3.11
uv sync --python 3.11 --extra kokoro --extra qwen --extra cpu
uv run --python 3.11 uvicorn app.main:app --reload
```

Frontend:

```bash
cd app/frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

## Python hooks

Install the Git hooks once from the repo root:

```bash
prek install
```

Run them manually across the tracked Python files when needed:

```bash
prek run --all-files
```

The repo uses Ruff for Python linting and formatting via [`.pre-commit-config.yaml`](/home/azam/development/text-to-speech-webui/.pre-commit-config.yaml), so routine style checks do not need ad hoc syntax-only verification commands.

## Tests

```bash
cd app/backend
uv python install 3.11
uv sync --python 3.11 --extra dev
uv run --python 3.11 pytest
```

## Kokoro setup

Prepare writable host runtime directories, then install the optional Kokoro runtime with CPU-only PyTorch and download the real Kokoro model files plus the required English spaCy model:

```bash
./scripts/download_kokoro.sh
```

The intended workflow is:

```bash
./scripts/download_kokoro.sh
docker compose up --build
```

This lets you fetch models on the host while you have network access, then run the container stack in offline mode using the downloaded files under `runtime/models`.

The backend now targets Python 3.11+ because the current Qwen CPU runtime depends on packages that do not publish usable Linux wheels for Python 3.10.

After those files are present, the backend will automatically use real Kokoro inference for the `kokoro` model. It only falls back to demo synthesis when Kokoro assets are missing and `DEMO_MODE=true`.

## Qwen setup

Download the Qwen3-TTS 0.6B custom-voice checkpoint for local CPU inference:

```bash
./scripts/download_qwen.sh
```

The default Compose stack now includes the Qwen CPU runtime. Once the model files are present under `runtime/models/qwen3_0_6b`, the backend will use real Qwen inference offline instead of demo synthesis.

The default Docker stack now runs with `DEMO_MODE=false`, so missing model assets or missing optional runtimes surface as explicit errors instead of silently falling back to the demo tone.

## Demo offline prep

```bash
uv python install 3.11
uv run --python 3.11 python scripts/preload_models.py --demo --model kokoro --model qwen3_0_6b
```

This writes local model placeholder manifests under `runtime/models`. Replace those directories with real model weights when wiring the actual Kokoro and Qwen runtimes.

## Docker

```bash
docker compose up --build
```

This starts:

- `frontend`: nginx serving the built React app on `http://127.0.0.1:3000`
- `backend`: FastAPI on the internal Compose network, proxied by the frontend container at `/api`

The default Compose stack is CPU-first and uses locally downloaded model files from the `runtime/` directory.
The backend Dockerfiles use BuildKit cache mounts for `uv`, so repeated image builds can reuse downloaded Python packages.

## Optional GPU Scaffold

There is also an optional override file and separate backend Dockerfile reserved for a future GPU-oriented backend path:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

That path is not the default deployment target and is intentionally separate from the main Kokoro CPU stack. For host-side development, the matching dependency split is:

```bash
cd app/backend
uv python install 3.11
uv sync --python 3.11 --extra kokoro --extra qwen --extra gpu
```

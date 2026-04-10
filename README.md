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

Download the Qwen3-TTS 0.6B checkpoints for both built-in named voices and saved voice cloning:

```bash
./scripts/download_qwen.sh
```

The default Compose stack now includes the Qwen CPU runtime. The script downloads:

- `runtime/models/qwen3_0_6b` for built-in named voices
- `runtime/models/qwen3_0_6b_base` for saved voice cloning

Once those directories are present, the backend can run both normal Qwen voice generation and saved voice cloning offline.

Voice cloning workflow:

1. Open the app and go to the Voice Lab panel.
2. Record or import a short single-speaker reference clip.
3. Enter the exact transcript for that recording.
4. Save the sample, then select `Qwen3-TTS 0.6B` with `Saved cloned voices` in the generation form.

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
The default backend image also uses a CPU-only Torch install and a multi-stage build to avoid shipping the larger GPU-oriented Python wheel set in the main Kokoro deployment.

## Optional GPU setup (ready-to-run)

The GPU path uses:

- `app/backend/Dockerfile.gpu` for the backend image
- `docker-compose.gpu.yml` as a Compose override that requests all host GPUs
- PyTorch CUDA 12.8 wheels from the `gpu` dependency extra in `app/backend/pyproject.toml`

### 1) Host prerequisites

1. Install an NVIDIA driver on the host and reboot.
2. Verify the driver sees your GPU:

   ```bash
   nvidia-smi
   ```

3. Install Docker Engine and Docker Compose plugin.
4. Install the NVIDIA Container Toolkit (nvidia runtime) and configure Docker to expose GPUs to containers.
   - Official install guide: <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html>
   - Official Docker runtime guide: <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/docker-specialized.html>

On Ubuntu, the minimal flow is:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

5. Confirm Docker can reach the GPU runtime:

```bash
docker run --rm --gpus all nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04 nvidia-smi
```

### 2) Prepare local model/runtime directories

```bash
./scripts/download_kokoro.sh
./scripts/download_qwen.sh
```

### 3) Launch the GPU compose stack

Use the base file plus the GPU override:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

Run detached:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d
```

Stop the stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml down
```

### 4) Validate GPU visibility inside backend container

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml exec backend nvidia-smi
```

And verify PyTorch sees CUDA:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml exec backend \
  uv run --no-sync python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no-cuda')"
```

If `torch.cuda.is_available()` is `False`, check driver/runtime installation on the host first, then confirm the compose command includes `-f docker-compose.gpu.yml`.

## Optional GPU Scaffold

For host-side local Python development (outside Docker), the matching dependency split is:

```bash
cd app/backend
uv python install 3.11
uv sync --python 3.11 --extra kokoro --extra qwen --extra gpu
```

That path is not the default deployment target and is intentionally separate from the main Kokoro CPU stack.
The GPU backend Dockerfile keeps the broader default Python dependency set intact.

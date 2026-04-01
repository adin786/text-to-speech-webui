# Project Notes

## Qwen Voice Cloning

- Qwen voice cloning uses `Qwen/Qwen3-TTS-12Hz-0.6B-Base` and the `generate_voice_clone(...)` API from `qwen-tts`.
- The built-in named speakers use `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` and `generate_custom_voice(...)`.
- This repo keeps both checkpoints:
  - `runtime/models/qwen3_0_6b` for built-in named voices
  - `runtime/models/qwen3_0_6b_base` for saved voice cloning
- Saved voices are persisted under `runtime/data/voices/<sample_id>/` as:
  - `reference.wav`
  - `metadata.json`
- The saved metadata stores the exact transcript alongside the recording because Qwen cloning quality depends on `ref_text` matching the reference audio.

## Voice Sample Guidance

- Prefer a clean single-speaker clip in a quiet room.
- Qwen shows cloning from a short reference clip; for this app, 5-15 seconds of clean speech is a safer practical target than trying to use the shortest possible sample.
- The transcript should match the recording exactly.
- Natural continuous speech is better than filler words, long pauses, overlapping speakers, music, or very noisy audio.

## GPU Docker Debug Quick Reference

### Files that control the GPU path

- Compose override: `docker-compose.gpu.yml`
- GPU backend image: `app/backend/Dockerfile.gpu`
- Python dependency source mapping for GPU wheels: `app/backend/pyproject.toml` (`gpu` extra uses the `pytorch-cu128` index)

### Expected host prerequisites

- NVIDIA driver installed and working (`nvidia-smi` on host).
- Docker Engine + Docker Compose plugin installed.
- NVIDIA Container Toolkit installed and runtime configured (`nvidia-ctk runtime configure --runtime=docker`).
- Docker daemon restarted after toolkit setup.

### Canonical bring-up commands

```bash
./scripts/download_kokoro.sh
./scripts/download_qwen.sh
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

### Canonical GPU verification commands

Host runtime verification:

```bash
docker run --rm --gpus all nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04 nvidia-smi
```

Container verification:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml exec backend nvidia-smi
docker compose -f docker-compose.yml -f docker-compose.gpu.yml exec backend \
  uv run --no-sync --python 3.11 python -c "import torch; print(torch.cuda.is_available()); print(torch.version.cuda)"
```

### Frequent failure modes and fixes

1. `could not select device driver "" with capabilities: [[gpu]]`
   - Cause: NVIDIA runtime/toolkit is not installed or not configured for Docker.
   - Fix: install `nvidia-container-toolkit`, run `sudo nvidia-ctk runtime configure --runtime=docker`, restart Docker.

2. `nvidia-smi` works on host but fails in container
   - Cause: compose stack launched without the GPU override.
   - Fix: always include both compose files: `-f docker-compose.yml -f docker-compose.gpu.yml`.

3. Backend starts but `torch.cuda.is_available()` is `False`
   - Cause: host runtime not wired through Docker or incompatible host driver.
   - Fix: re-check host/container `nvidia-smi`; validate driver compatibility with CUDA 12.8 runtime.

4. Build fails while resolving/installing GPU PyTorch wheels
   - Cause: network outage, index access issues, or lock/dependency mismatch.
   - Fix: verify internet access to `https://download.pytorch.org/whl/cu128`, then rebuild with `--no-cache` for a clean retry.

5. Build fails around Python version
   - Cause: the GPU Docker image must run on Python 3.11 to match lock/runtime expectations.
   - Fix: keep `app/backend/Dockerfile.gpu` on Python 3.11 and use `uv ... --python 3.11` in sync/run commands.

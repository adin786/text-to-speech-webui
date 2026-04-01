#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backend_dir="$repo_root/app/backend"
models_root="$repo_root/runtime/models"

"$repo_root/scripts/prepare_runtime.sh"

cd "$backend_dir"
uv sync --extra kokoro --extra cpu
uv run python ../../scripts/preload_models.py --root "$models_root" --model kokoro

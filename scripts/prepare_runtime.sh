#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ensure_writable_dir() {
  local dir="$1"

  mkdir -p "$dir"

  if [[ ! -w "$dir" ]]; then
    cat >&2 <<EOF
Runtime path is not writable: $dir

This usually means Docker created the runtime directory as root on a previous run.
Fix it once with:

  sudo chown -R "\$USER":"\$USER" "$repo_root/runtime"
EOF
    exit 1
  fi
}

ensure_writable_dir "$repo_root/runtime/models"
ensure_writable_dir "$repo_root/runtime/output"
ensure_writable_dir "$repo_root/runtime/data/jobs"
ensure_writable_dir "$repo_root/runtime/logs"

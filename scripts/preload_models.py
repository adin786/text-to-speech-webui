from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare local model directories for offline use.")
    parser.add_argument("--root", default="runtime/models", help="Model root directory.")
    parser.add_argument(
        "--model",
        action="append",
        dest="models",
        default=[],
        help="Model id to prepare. Can be passed multiple times.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Write demo manifests only instead of downloading real model weights.",
    )
    args = parser.parse_args()

    root = Path(args.root)
    models = args.models or ["kokoro"]
    root.mkdir(parents=True, exist_ok=True)

    for model in models:
        model_dir = root / model
        model_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "model": model,
            "mode": "demo" if args.demo else "placeholder",
            "message": "Replace this directory with actual model weights for production offline use.",
        }
        (model_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print(f"Prepared {model_dir}")


if __name__ == "__main__":
    main()

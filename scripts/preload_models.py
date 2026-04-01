from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

KOKORO_REPO_ID = "hexgrad/Kokoro-82M"
KOKORO_FILES = [
    "config.json",
    "kokoro-v1_0.pth",
    "voices/af_alloy.pt",
    "voices/af_sarah.pt",
    "voices/am_adam.pt",
    "voices/bf_emma.pt",
]

QWEN_REPO_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
QWEN_FILES = [
    "config.json",
    "generation_config.json",
    "merges.txt",
    "model.safetensors",
    "preprocessor_config.json",
    "tokenizer_config.json",
    "vocab.json",
    "speech_tokenizer/config.json",
    "speech_tokenizer/configuration.json",
    "speech_tokenizer/model.safetensors",
    "speech_tokenizer/preprocessor_config.json",
]


def download_kokoro(model_dir: Path) -> None:
    from huggingface_hub import hf_hub_download

    for filename in KOKORO_FILES:
        destination = model_dir / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        hf_hub_download(
            repo_id=KOKORO_REPO_ID,
            filename=filename,
            local_dir=str(model_dir),
        )
        print(f"Downloaded {filename}")

    ensure_spacy_model()


def ensure_spacy_model() -> None:
    try:
        import spacy.util
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "spaCy is required before downloading Kokoro assets."
        ) from exc

    if spacy.util.is_package("en_core_web_sm"):
        print("spaCy model en_core_web_sm already installed")
        return

    subprocess.run(
        [sys.executable, "-m", "spacy", "download", "en_core_web_sm"],
        check=True,
    )


def download_qwen(model_dir: Path) -> None:
    from huggingface_hub import hf_hub_download

    for filename in QWEN_FILES:
        destination = model_dir / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        hf_hub_download(
            repo_id=QWEN_REPO_ID,
            filename=filename,
            local_dir=str(model_dir),
        )
        print(f"Downloaded {filename}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare local model directories for offline use."
    )
    parser.add_argument(
        "--root", default="runtime/models", help="Model root directory."
    )
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
        if not args.demo and model == "kokoro":
            download_kokoro(model_dir)
            continue
        if not args.demo and model == "qwen3_0_6b":
            download_qwen(model_dir)
            continue
        manifest = {
            "model": model,
            "mode": "demo" if args.demo else "placeholder",
            "message": "Replace this directory with actual model weights for production offline use.",
        }
        (model_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print(f"Prepared {model_dir}")


if __name__ == "__main__":
    main()

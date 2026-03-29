from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.domain.errors import RuntimeFailure


class AudioProcessor:
    def __init__(self, ffmpeg_binary: str, preserve_wav: bool = False) -> None:
        self.ffmpeg_binary = ffmpeg_binary
        self.preserve_wav = preserve_wav

    def normalize_wav(self, wav_path: Path) -> Path:
        if not wav_path.exists():
            raise RuntimeFailure("wav_missing", "The generated WAV file is missing.", status_code=500)
        return wav_path

    def encode_mp3(self, wav_path: Path, mp3_path: Path) -> None:
        if not shutil.which(self.ffmpeg_binary):
            raise RuntimeFailure("ffmpeg_missing", "ffmpeg is required to encode MP3 output.", status_code=500)
        mp3_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                self.ffmpeg_binary,
                "-y",
                "-i",
                str(wav_path),
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(mp3_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeFailure("ffmpeg_failed", result.stderr.strip() or "ffmpeg failed.", status_code=500)

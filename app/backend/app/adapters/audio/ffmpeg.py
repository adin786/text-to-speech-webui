from __future__ import annotations

import contextlib
import shutil
import subprocess
import wave
from pathlib import Path

from app.domain.errors import RuntimeFailure


class AudioProcessor:
    def __init__(self, ffmpeg_binary: str, preserve_wav: bool = False) -> None:
        self.ffmpeg_binary = ffmpeg_binary
        self.preserve_wav = preserve_wav

    def normalize_wav(self, wav_path: Path) -> Path:
        if not wav_path.exists():
            raise RuntimeFailure(
                "wav_missing", "The generated WAV file is missing.", status_code=500
            )
        return wav_path

    def normalize_reference_audio(self, source_path: Path, wav_path: Path) -> Path:
        self._require_binary()
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                self.ffmpeg_binary,
                "-y",
                "-i",
                str(source_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(wav_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeFailure(
                "reference_audio_invalid",
                result.stderr.strip() or "Could not process the voice sample.",
                status_code=400,
            )
        return wav_path

    def wav_duration_seconds(self, wav_path: Path) -> float:
        with contextlib.closing(wave.open(str(wav_path), "rb")) as handle:
            frames = handle.getnframes()
            rate = handle.getframerate()
            if rate <= 0:
                raise RuntimeFailure(
                    "reference_audio_invalid",
                    "The saved voice sample has an invalid sample rate.",
                    status_code=400,
                )
            return round(frames / rate, 2)

    def encode_mp3(self, wav_path: Path, mp3_path: Path) -> None:
        self._require_binary()
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
            raise RuntimeFailure(
                "ffmpeg_failed",
                result.stderr.strip() or "ffmpeg failed.",
                status_code=500,
            )

    def _require_binary(self) -> None:
        if not shutil.which(self.ffmpeg_binary):
            raise RuntimeFailure(
                "ffmpeg_missing",
                "ffmpeg is required to process audio.",
                status_code=500,
            )

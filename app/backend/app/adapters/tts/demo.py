from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


def synthesize_demo_wave(
    text: str, destination: Path, base_frequency: int = 220, speed: float = 1.0
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 24_000
    frames: list[int] = []
    amplitude = 10_000
    text = text[:400]
    character_duration = max(0.04, 0.08 / speed)

    for index, character in enumerate(text):
        frequency = base_frequency + (ord(character) % 30) * 8 + (index % 5) * 5
        duration = character_duration
        total_samples = int(sample_rate * duration)
        for position in range(total_samples):
            envelope = min(position / 400, 1) * min((total_samples - position) / 400, 1)
            sample = int(
                amplitude
                * envelope
                * math.sin(2 * math.pi * frequency * position / sample_rate)
            )
            frames.append(sample)
        pause_samples = int(sample_rate * 0.01)
        frames.extend([0] * pause_samples)

    with wave.open(str(destination), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        pcm = b"".join(struct.pack("<h", frame) for frame in frames)
        wav_file.writeframes(pcm)

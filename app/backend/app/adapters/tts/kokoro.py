from __future__ import annotations

from functools import lru_cache
import importlib.util
from pathlib import Path
from threading import Lock

from app.adapters.tts.base import TTSBackend
from app.adapters.tts.demo import synthesize_demo_wave
from app.domain.errors import AvailabilityError, RuntimeFailure
from app.domain.models import BackendSynthesisOutput, ModelId, SynthesisJob, VoiceDescriptor

VOICE_OPTIONS = [
    VoiceDescriptor(id="af_alloy", display_name="Alloy"),
    VoiceDescriptor(id="af_sarah", display_name="Sarah"),
    VoiceDescriptor(id="am_adam", display_name="Adam"),
    VoiceDescriptor(id="bf_emma", display_name="Emma"),
]


class KokoroBackend(TTSBackend):
    model_id = ModelId.KOKORO
    display_name = "Kokoro"
    runtime = "cpu"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._lock = Lock()
        self._model = None
        self._pipeline = None

    def is_enabled(self) -> bool:
        return self.settings.enable_kokoro

    def is_available(self) -> bool:
        if self._has_runtime() and self._has_local_assets():
            return True
        if self.settings.demo_mode:
            return True
        return False

    def notes(self) -> str | None:
        if self._has_runtime() and self._has_local_assets():
            return "CPU-first local backend using downloaded Kokoro weights."
        if self.settings.demo_mode:
            return "Demo synthesis is active until Kokoro weights are installed."
        return "Kokoro runtime or model files are missing locally."

    def list_languages(self) -> list[str]:
        return ["en"]

    def list_voices(self) -> list[VoiceDescriptor]:
        return VOICE_OPTIONS

    def synthesize_to_wav(self, job: SynthesisJob) -> BackendSynthesisOutput:
        if self._has_runtime() and self._has_local_assets():
            return self._synthesize_real(job)
        if not self.settings.demo_mode:
            raise AvailabilityError(
                "kokoro_missing_assets",
                "Kokoro is enabled but the local model files are missing.",
                status_code=409,
            )
        output = self.output_wav_path(job.job_id)
        synthesize_demo_wave(
            text=job.request.text,
            destination=output,
            base_frequency=210,
            speed=job.request.speed,
        )
        return BackendSynthesisOutput(
            wav_path=output,
            metadata={"backend": "kokoro", "mode": "demo" if self.settings.demo_mode else "local"},
        )

    def _synthesize_real(self, job: SynthesisJob) -> BackendSynthesisOutput:
        import soundfile as sf

        model = self._get_model()
        pipeline = self._get_pipeline()
        voice = job.request.voice or VOICE_OPTIONS[0].id
        voice_pack = self._load_voice_pack(voice)
        output = self.output_wav_path(job.job_id)
        output.parent.mkdir(parents=True, exist_ok=True)

        chunks = []
        for result in pipeline(job.request.text, voice=voice_pack, speed=job.request.speed, model=model):
            if result.audio is None:
                continue
            chunks.append(result.audio.numpy())

        if not chunks:
            raise RuntimeFailure("kokoro_empty_output", "Kokoro did not generate audio.", status_code=500)

        waveform = chunks[0] if len(chunks) == 1 else __import__("numpy").concatenate(chunks)
        sf.write(output, waveform, 24_000)
        return BackendSynthesisOutput(
            wav_path=output,
            metadata={"backend": "kokoro", "mode": "real", "voice": voice},
        )

    def _has_runtime(self) -> bool:
        return all(
            importlib.util.find_spec(module_name) is not None
            for module_name in ("kokoro", "soundfile", "torch")
        )

    def _has_local_assets(self) -> bool:
        model_dir = self.model_store.model_dir(self.settings.kokoro_model_dir_name)
        required_paths = [
            model_dir / "config.json",
            model_dir / "kokoro-v1_0.pth",
        ]
        required_paths.extend(self._voice_path(voice.id) for voice in VOICE_OPTIONS)
        return all(path.exists() for path in required_paths)

    def _voice_path(self, voice_id: str) -> Path:
        return self.model_store.model_dir(self.settings.kokoro_model_dir_name) / "voices" / f"{voice_id}.pt"

    def _get_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from kokoro import KModel

                    model_dir = self.model_store.model_dir(self.settings.kokoro_model_dir_name)
                    self._model = KModel(
                        repo_id="hexgrad/Kokoro-82M",
                        config=str(model_dir / "config.json"),
                        model=str(model_dir / "kokoro-v1_0.pth"),
                    ).to("cpu").eval()
        return self._model

    def _get_pipeline(self):
        if self._pipeline is None:
            with self._lock:
                if self._pipeline is None:
                    from kokoro import KPipeline

                    self._pipeline = KPipeline(
                        lang_code="a",
                        repo_id="hexgrad/Kokoro-82M",
                        model=False,
                        device="cpu",
                    )
        return self._pipeline

    @lru_cache(maxsize=8)
    def _load_voice_pack(self, voice_id: str):
        import torch

        voice_path = self._voice_path(voice_id)
        if not voice_path.exists():
            raise AvailabilityError(
                "kokoro_voice_missing",
                f"Kokoro voice file {voice_id} is missing from local storage.",
                status_code=409,
            )
        return torch.load(voice_path, map_location="cpu", weights_only=True)

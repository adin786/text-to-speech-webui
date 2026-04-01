from __future__ import annotations

import importlib.util
from threading import Lock

from app.adapters.tts.base import TTSBackend
from app.adapters.tts.demo import synthesize_demo_wave
from app.domain.errors import AvailabilityError, RuntimeFailure
from app.domain.models import (
    BackendSynthesisOutput,
    ModelId,
    SynthesisJob,
    VoiceDescriptor,
)

VOICE_OPTIONS = [
    VoiceDescriptor(id="Ryan", display_name="Ryan"),
    VoiceDescriptor(id="Aiden", display_name="Aiden"),
    VoiceDescriptor(id="Vivian", display_name="Vivian"),
    VoiceDescriptor(id="Serena", display_name="Serena"),
    VoiceDescriptor(id="Uncle_Fu", display_name="Uncle Fu"),
    VoiceDescriptor(id="Dylan", display_name="Dylan"),
    VoiceDescriptor(id="Eric", display_name="Eric"),
    VoiceDescriptor(id="Ono_Anna", display_name="Ono Anna"),
    VoiceDescriptor(id="Sohee", display_name="Sohee"),
]

REQUIRED_PATHS = [
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


class QwenBackend(TTSBackend):
    model_id = ModelId.QWEN
    display_name = "Qwen3-TTS 0.6B"
    runtime = "cpu"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._lock = Lock()
        self._model = None

    def is_enabled(self) -> bool:
        return self.settings.enable_qwen and self.settings.qwen_enabled_in_ui

    def is_available(self) -> bool:
        if self._has_runtime() and self._has_local_assets():
            return True
        if self.settings.demo_mode:
            return True
        return False

    def notes(self) -> str | None:
        if self._has_runtime() and self._has_local_assets():
            return "CPU-first local backend using downloaded Qwen3-TTS 0.6B weights."
        if self.settings.demo_mode:
            return "Demo synthesis is active until Qwen weights are installed."
        return "Qwen runtime or model files are missing locally."

    def list_languages(self) -> list[str]:
        return ["Auto", "en", "de", "fr", "es", "zh", "ja", "ko", "pt", "it", "ru"]

    def list_voices(self) -> list[VoiceDescriptor]:
        return VOICE_OPTIONS

    def synthesize_to_wav(self, job: SynthesisJob) -> BackendSynthesisOutput:
        if self._has_runtime() and self._has_local_assets():
            return self._synthesize_real(job)
        if not self.settings.demo_mode:
            raise AvailabilityError(
                "qwen_missing_assets",
                "Qwen is enabled but the local model files are missing.",
                status_code=409,
            )
        output = self.output_wav_path(job.job_id)
        synthesize_demo_wave(
            text=job.request.text,
            destination=output,
            base_frequency=300,
            speed=job.request.speed,
        )
        return BackendSynthesisOutput(
            wav_path=output,
            metadata={
                "backend": "qwen3_0_6b",
                "mode": "demo" if self.settings.demo_mode else "local",
            },
        )

    def _has_runtime(self) -> bool:
        return all(
            importlib.util.find_spec(module_name) is not None
            for module_name in ("qwen_tts", "soundfile", "torch")
        )

    def _has_local_assets(self) -> bool:
        model_dir = self.model_store.model_dir(self.settings.qwen_model_dir_name)
        return all(
            (model_dir / relative_path).exists() for relative_path in REQUIRED_PATHS
        )

    def _get_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    import torch
                    from qwen_tts import Qwen3TTSModel

                    model_dir = self.model_store.model_dir(
                        self.settings.qwen_model_dir_name
                    )
                    self._model = Qwen3TTSModel.from_pretrained(
                        str(model_dir),
                        device_map="cpu",
                        dtype=torch.float32,
                        local_files_only=True,
                    )
        return self._model

    def _synthesize_real(self, job: SynthesisJob) -> BackendSynthesisOutput:
        import soundfile as sf

        model = self._get_model()
        output = self.output_wav_path(job.job_id)
        output.parent.mkdir(parents=True, exist_ok=True)

        speaker = job.request.voice or VOICE_OPTIONS[0].id
        language = (
            "Auto"
            if not job.request.language or job.request.language.lower() == "auto"
            else job.request.language
        )
        wavs, sample_rate = model.generate_custom_voice(
            text=job.request.text,
            language=language,
            speaker=speaker,
        )
        if not wavs:
            raise RuntimeFailure(
                "qwen_empty_output", "Qwen did not generate audio.", status_code=500
            )
        waveform = wavs[0]
        sf.write(output, waveform, sample_rate)
        return BackendSynthesisOutput(
            wav_path=output,
            metadata={
                "backend": "qwen3_0_6b",
                "mode": "real",
                "voice": speaker,
                "language": language,
            },
        )

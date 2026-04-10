from __future__ import annotations

import importlib.util
from threading import Lock

from app.adapters.tts.base import TTSBackend
from app.adapters.tts.demo import synthesize_demo_wave
from app.domain.errors import AvailabilityError, RuntimeFailure, ValidationError
from app.domain.models import (
    BackendSynthesisOutput,
    ModelId,
    SynthesisJob,
    SynthesisRequest,
    VoiceDescriptor,
)
from app.services.voices import VoiceSampleService

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

QWEN_REQUIRED_PATHS = [
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

LANGUAGE_NAMES = {
    "auto": "Auto",
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "pt": "Portuguese",
    "it": "Italian",
    "ru": "Russian",
}


class QwenBackend(TTSBackend):
    model_id = ModelId.QWEN
    display_name = "Qwen3-TTS 0.6B"
    runtime = "cpu"

    def __init__(
        self,
        *args,
        voice_sample_service: VoiceSampleService,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.voice_sample_service = voice_sample_service
        self._lock = Lock()
        self._custom_voice_model = None
        self._clone_model = None

    def is_enabled(self) -> bool:
        return self.settings.enable_qwen and self.settings.qwen_enabled_in_ui

    def is_available(self) -> bool:
        if self._has_runtime() and (
            self._has_custom_voice_assets() or self._has_clone_assets()
        ):
            return True
        if self.settings.demo_mode:
            return True
        return False

    def notes(self) -> str | None:
        if self._has_runtime():
            paths = []
            if self._has_custom_voice_assets():
                paths.append("named voices ready")
            if self._has_clone_assets():
                paths.append("voice cloning ready")
            if paths:
                return f"CPU-first local backend with {', '.join(paths)}."
        if self.settings.demo_mode:
            return "Demo synthesis is active until Qwen weights are installed."
        return "Qwen runtime or one of the required local checkpoints is missing."

    def list_languages(self) -> list[str]:
        return ["Auto", "en", "de", "fr", "es", "zh", "ja", "ko", "pt", "it", "ru"]

    def list_voices(self) -> list[VoiceDescriptor]:
        return VOICE_OPTIONS

    def validate_request(self, request: SynthesisRequest) -> None:
        if request.saved_voice_id:
            self.voice_sample_service.get_sample(request.saved_voice_id)
            if self._can_fallback_to_demo():
                return
            if not self._has_runtime() or not self._has_clone_assets():
                raise AvailabilityError(
                    "qwen_voice_clone_unavailable",
                    "Qwen voice cloning needs the Qwen Base checkpoint downloaded locally.",
                    status_code=409,
                )
            return

        if request.voice and request.voice not in {voice.id for voice in VOICE_OPTIONS}:
            raise ValidationError(
                "qwen_voice_invalid",
                "The selected built-in Qwen voice is not supported.",
                status_code=400,
            )
        if self._can_fallback_to_demo():
            return
        if not self._has_runtime() or not self._has_custom_voice_assets():
            raise AvailabilityError(
                "qwen_missing_assets",
                "Qwen custom voice generation needs the CustomVoice checkpoint downloaded locally.",
                status_code=409,
            )

    def synthesize_to_wav(self, job: SynthesisJob) -> BackendSynthesisOutput:
        if job.request.saved_voice_id:
            if self._has_runtime() and self._has_clone_assets():
                return self._synthesize_voice_clone(job)
            if not self.settings.demo_mode:
                raise AvailabilityError(
                    "qwen_voice_clone_unavailable",
                    "Qwen voice cloning needs the Qwen Base checkpoint downloaded locally.",
                    status_code=409,
                )
            return self._synthesize_demo(job, mode="demo_clone")

        if self._has_runtime() and self._has_custom_voice_assets():
            return self._synthesize_custom_voice(job)
        if not self.settings.demo_mode:
            raise AvailabilityError(
                "qwen_missing_assets",
                "Qwen custom voice generation needs the CustomVoice checkpoint downloaded locally.",
                status_code=409,
            )
        return self._synthesize_demo(job, mode="demo")

    def _synthesize_demo(self, job: SynthesisJob, mode: str) -> BackendSynthesisOutput:
        output = self.output_wav_path(job.job_id)
        synthesize_demo_wave(
            text=job.request.text,
            destination=output,
            base_frequency=300,
            speed=job.request.speed,
        )
        return BackendSynthesisOutput(
            wav_path=output,
            metadata={"backend": "qwen3_0_6b", "mode": mode},
        )

    def _has_runtime(self) -> bool:
        return all(
            importlib.util.find_spec(module_name) is not None
            for module_name in ("qwen_tts", "soundfile", "torch")
        )

    def _has_custom_voice_assets(self) -> bool:
        model_dir = self.model_store.model_dir(self.settings.qwen_model_dir_name)
        return all(
            (model_dir / relative_path).exists()
            for relative_path in QWEN_REQUIRED_PATHS
        )

    def _has_clone_assets(self) -> bool:
        model_dir = self.model_store.model_dir(self.settings.qwen_clone_model_dir_name)
        return all(
            (model_dir / relative_path).exists()
            for relative_path in QWEN_REQUIRED_PATHS
        )

    def _can_fallback_to_demo(self) -> bool:
        return self.settings.demo_mode

    def _load_model(self, kind: str):
        with self._lock:
            if kind == "custom" and self._custom_voice_model is None:
                self._custom_voice_model = self._create_model(
                    self.settings.qwen_model_dir_name
                )
            if kind == "clone" and self._clone_model is None:
                self._clone_model = self._create_model(
                    self.settings.qwen_clone_model_dir_name
                )
        return self._custom_voice_model if kind == "custom" else self._clone_model

    def _create_model(self, model_dir_name: str):
        import torch
        from qwen_tts import Qwen3TTSModel

        model_dir = self.model_store.model_dir(model_dir_name)
        return Qwen3TTSModel.from_pretrained(
            str(model_dir),
            device_map="cpu",
            dtype=torch.float32,
            local_files_only=True,
        )

    def _synthesize_custom_voice(self, job: SynthesisJob) -> BackendSynthesisOutput:
        import soundfile as sf

        model = self._load_model("custom")
        output = self.output_wav_path(job.job_id)
        output.parent.mkdir(parents=True, exist_ok=True)
        speaker = job.request.voice or VOICE_OPTIONS[0].id
        language = self._language_name(job.request.language)
        generate_kwargs = self._generation_kwargs(job.request)
        wavs, sample_rate = model.generate_custom_voice(
            text=job.request.text,
            language=language,
            speaker=speaker,
            **generate_kwargs,
        )
        if not wavs:
            raise RuntimeFailure(
                "qwen_empty_output", "Qwen did not generate audio.", status_code=500
            )
        sf.write(output, wavs[0], sample_rate)
        return BackendSynthesisOutput(
            wav_path=output,
            metadata={
                "backend": "qwen3_0_6b",
                "mode": "custom_voice",
                "voice": speaker,
                "language": language,
                "qwen_generation": generate_kwargs,
            },
        )

    def _synthesize_voice_clone(self, job: SynthesisJob) -> BackendSynthesisOutput:
        import soundfile as sf

        sample_id = job.request.saved_voice_id
        if sample_id is None:
            raise ValidationError(
                "qwen_voice_clone_missing",
                "A saved voice sample is required for voice cloning.",
                status_code=400,
            )
        sample = self.voice_sample_service.get_sample(sample_id)
        ref_audio = self.voice_sample_service.get_audio_path(sample_id)
        model = self._load_model("clone")
        output = self.output_wav_path(job.job_id)
        output.parent.mkdir(parents=True, exist_ok=True)
        language = self._language_name(job.request.language)
        generate_kwargs = self._generation_kwargs(job.request)
        wavs, sample_rate = model.generate_voice_clone(
            text=job.request.text,
            language=language,
            ref_audio=str(ref_audio),
            ref_text=sample.transcript,
            x_vector_only_mode=job.request.qwen_x_vector_only_mode,
            **generate_kwargs,
        )
        if not wavs:
            raise RuntimeFailure(
                "qwen_empty_output", "Qwen did not generate audio.", status_code=500
            )
        sf.write(output, wavs[0], sample_rate)
        return BackendSynthesisOutput(
            wav_path=output,
            metadata={
                "backend": "qwen3_0_6b",
                "mode": "voice_clone",
                "saved_voice_id": sample.sample_id,
                "saved_voice_name": sample.name,
                "language": language,
                "qwen_generation": {
                    **generate_kwargs,
                    "x_vector_only_mode": job.request.qwen_x_vector_only_mode,
                },
            },
        )

    def _language_name(self, value: str | None) -> str:
        if value is None:
            return "Auto"
        return LANGUAGE_NAMES.get(value.lower(), value)

    def _generation_kwargs(self, request: SynthesisRequest) -> dict[str, int | float | bool]:
        return {
            "non_streaming_mode": request.qwen_non_streaming_mode,
            "do_sample": request.qwen_do_sample,
            "top_k": request.qwen_top_k,
            "top_p": request.qwen_top_p,
            "temperature": request.qwen_temperature,
            "repetition_penalty": request.qwen_repetition_penalty,
            "subtalker_dosample": request.qwen_subtalker_do_sample,
            "subtalker_top_k": request.qwen_subtalker_top_k,
            "subtalker_top_p": request.qwen_subtalker_top_p,
            "subtalker_temperature": request.qwen_subtalker_temperature,
            "max_new_tokens": request.qwen_max_new_tokens,
        }

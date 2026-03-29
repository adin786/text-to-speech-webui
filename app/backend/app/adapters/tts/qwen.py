from __future__ import annotations

from app.adapters.tts.base import TTSBackend
from app.adapters.tts.demo import synthesize_demo_wave
from app.domain.models import BackendSynthesisOutput, ModelId, SynthesisJob, VoiceDescriptor


class QwenBackend(TTSBackend):
    model_id = ModelId.QWEN
    display_name = "Qwen3-TTS 0.6B"
    runtime = "gpu"

    def is_enabled(self) -> bool:
        return self.settings.enable_qwen and self.settings.qwen_enabled_in_ui

    def is_available(self) -> bool:
        if self.settings.demo_mode:
            return self.model_store.model_dir(self.settings.qwen_model_dir_name).exists()
        return self.model_store.model_dir(self.settings.qwen_model_dir_name).exists()

    def notes(self) -> str | None:
        if not self.is_available():
            return "Qwen is optional and is not installed locally."
        if self.settings.demo_mode:
            return "Demo synthesis is active until the Qwen runtime is installed."
        return "Optional advanced backend."

    def list_languages(self) -> list[str]:
        return ["en", "de", "fr", "es", "zh"]

    def list_voices(self) -> list[VoiceDescriptor]:
        return [
            VoiceDescriptor(id="aurora", display_name="Aurora"),
            VoiceDescriptor(id="atlas", display_name="Atlas"),
        ]

    def synthesize_to_wav(self, job: SynthesisJob) -> BackendSynthesisOutput:
        output = self.output_wav_path(job.job_id)
        synthesize_demo_wave(
            text=job.request.text,
            destination=output,
            base_frequency=300,
            speed=job.request.speed,
        )
        return BackendSynthesisOutput(
            wav_path=output,
            metadata={"backend": "qwen3_0_6b", "mode": "demo" if self.settings.demo_mode else "local"},
        )

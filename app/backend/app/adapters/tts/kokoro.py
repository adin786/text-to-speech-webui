from __future__ import annotations

from app.adapters.tts.base import TTSBackend
from app.adapters.tts.demo import synthesize_demo_wave
from app.domain.models import BackendSynthesisOutput, ModelId, SynthesisJob, VoiceDescriptor


class KokoroBackend(TTSBackend):
    model_id = ModelId.KOKORO
    display_name = "Kokoro"
    runtime = "cpu"

    def is_enabled(self) -> bool:
        return self.settings.enable_kokoro

    def is_available(self) -> bool:
        if self.settings.demo_mode:
            return True
        return self.model_store.model_dir(self.settings.kokoro_model_dir_name).exists()

    def notes(self) -> str | None:
        if self.settings.demo_mode:
            return "Demo synthesis is active until Kokoro weights are installed."
        if not self.is_available():
            return "Kokoro model files are not installed locally."
        return "CPU-first local backend."

    def list_languages(self) -> list[str]:
        return ["en"]

    def list_voices(self) -> list[VoiceDescriptor]:
        return [
            VoiceDescriptor(id="alloy", display_name="Alloy"),
            VoiceDescriptor(id="luna", display_name="Luna"),
        ]

    def synthesize_to_wav(self, job: SynthesisJob) -> BackendSynthesisOutput:
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

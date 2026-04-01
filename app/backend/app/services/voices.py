from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.adapters.audio.ffmpeg import AudioProcessor
from app.adapters.storage.filesystem import VoiceSampleStore
from app.domain.errors import NotFoundError, ValidationError
from app.domain.models import VoiceSample


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VoiceSampleService:
    def __init__(
        self,
        store: VoiceSampleStore,
        audio_processor: AudioProcessor,
    ) -> None:
        self.store = store
        self.audio_processor = audio_processor

    def list_samples(self) -> list[VoiceSample]:
        return self.store.list_samples()

    def get_sample(self, sample_id: str) -> VoiceSample:
        sample = self.store.get_sample(sample_id)
        if sample is None:
            raise NotFoundError(
                "voice_sample_not_found",
                f"Saved voice sample {sample_id} was not found.",
                status_code=404,
            )
        sample.audio_url = f"/api/voices/{sample.sample_id}/audio"
        return sample

    def get_audio_path(self, sample_id: str) -> Path:
        self.get_sample(sample_id)
        path = self.store.audio_path(sample_id)
        if not path.exists():
            raise NotFoundError(
                "voice_sample_audio_not_found",
                f"Saved voice sample {sample_id} has no audio.",
                status_code=404,
            )
        return path

    def create_sample(
        self, name: str, transcript: str, audio_bytes: bytes
    ) -> VoiceSample:
        normalized_name = self._validate_name(name)
        normalized_transcript = self._validate_transcript(transcript)
        if not audio_bytes:
            raise ValidationError(
                "voice_sample_audio_required",
                "A recorded or uploaded voice sample is required.",
                status_code=400,
            )

        sample_id = self.store.create_sample_id()
        with NamedTemporaryFile(
            "wb", dir=self.store.root, prefix=f"{sample_id}-upload-", delete=False
        ) as handle:
            handle.write(audio_bytes)
            source_path = Path(handle.name)

        try:
            target_path = self.store.audio_path(sample_id)
            normalized_audio = self.audio_processor.normalize_reference_audio(
                source_path, target_path
            )
        finally:
            source_path.unlink(missing_ok=True)

        duration_seconds = self.audio_processor.wav_duration_seconds(normalized_audio)
        now = utcnow()
        sample = VoiceSample(
            sample_id=sample_id,
            name=normalized_name,
            transcript=normalized_transcript,
            duration_seconds=duration_seconds,
            created_at=now,
            updated_at=now,
            audio_url=f"/api/voices/{sample_id}/audio",
        )
        self.store.save_sample(sample)
        return sample

    def update_sample(
        self, sample_id: str, name: str | None, transcript: str | None
    ) -> VoiceSample:
        sample = self.get_sample(sample_id)
        updated = sample.model_copy(
            update={
                "name": self._validate_name(name) if name is not None else sample.name,
                "transcript": (
                    self._validate_transcript(transcript)
                    if transcript is not None
                    else sample.transcript
                ),
                "updated_at": utcnow(),
                "audio_url": f"/api/voices/{sample_id}/audio",
            }
        )
        self.store.save_sample(updated)
        return updated

    def delete_sample(self, sample_id: str) -> None:
        self.get_sample(sample_id)
        self.store.delete_sample(sample_id)

    def _validate_name(self, value: str | None) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise ValidationError(
                "voice_sample_name_required",
                "Saved voice samples need a name.",
                status_code=400,
            )
        if len(normalized) > 80:
            raise ValidationError(
                "voice_sample_name_too_long",
                "Saved voice sample names must be 80 characters or fewer.",
                status_code=400,
            )
        return normalized

    def _validate_transcript(self, value: str | None) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise ValidationError(
                "voice_sample_transcript_required",
                "A transcript that matches the reference recording is required.",
                status_code=400,
            )
        if len(normalized) > 500:
            raise ValidationError(
                "voice_sample_transcript_too_long",
                "Voice sample transcripts must be 500 characters or fewer.",
                status_code=400,
            )
        return normalized

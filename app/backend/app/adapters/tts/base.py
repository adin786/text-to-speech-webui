from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.adapters.storage.filesystem import ModelStore
from app.core.config import Settings
from app.domain.models import (
    BackendSynthesisOutput,
    ModelDescriptor,
    ModelId,
    SynthesisJob,
    VoiceDescriptor,
)


class TTSBackend(ABC):
    model_id: ModelId
    display_name: str
    runtime: str

    def __init__(self, settings: Settings, model_store: ModelStore) -> None:
        self.settings = settings
        self.model_store = model_store

    @abstractmethod
    def is_enabled(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def notes(self) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def list_languages(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def list_voices(self) -> list[VoiceDescriptor]:
        raise NotImplementedError

    @abstractmethod
    def synthesize_to_wav(self, job: SynthesisJob) -> BackendSynthesisOutput:
        raise NotImplementedError

    def describe(self) -> ModelDescriptor:
        return ModelDescriptor(
            id=self.model_id,
            display_name=self.display_name,
            available=self.is_available(),
            enabled=self.is_enabled(),
            runtime=self.runtime,
            languages=self.list_languages(),
            voices=self.list_voices(),
            notes=self.notes(),
        )

    def output_wav_path(self, job_id: str) -> Path:
        return self.settings.output_root / f"{job_id}-{self.model_id.value}.wav"

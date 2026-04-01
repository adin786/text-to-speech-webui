from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from app.domain.errors import ValidationError


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ModelId(str, Enum):
    KOKORO = "kokoro"
    QWEN = "qwen3_0_6b"


class JobStatus(str, Enum):
    QUEUED = "queued"
    VALIDATING = "validating"
    RUNNING = "running"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AppConfig(BaseModel):
    app_title: str
    offline_mode: bool
    default_model: str
    max_input_length: int
    keep_history_limit: int


class VoiceDescriptor(BaseModel):
    id: str
    display_name: str


class ModelDescriptor(BaseModel):
    id: ModelId
    display_name: str
    available: bool
    enabled: bool
    runtime: str
    languages: list[str]
    voices: list[VoiceDescriptor]
    notes: str | None = None


class SynthesisRequest(BaseModel):
    text: str
    model: ModelId = ModelId.KOKORO
    voice: str | None = None
    language: str | None = "en"
    speed: float = 1.0
    output_format: str = "mp3"
    title: str | None = None

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Text is required.")
        return value.strip()

    @field_validator("speed")
    @classmethod
    def validate_speed(cls, value: float) -> float:
        if value <= 0 or value > 3:
            raise ValueError("Speed must be between 0 and 3.")
        return value

    @field_validator("output_format")
    @classmethod
    def validate_output_format(cls, value: str) -> str:
        if value != "mp3":
            raise ValueError("Only MP3 output is supported in v1.")
        return value


class AudioArtifact(BaseModel):
    wav_path: Path
    mp3_path: Path
    preview_url: str
    download_url: str
    file_name: str
    size_bytes: int


class SynthesisResult(BaseModel):
    artifact: AudioArtifact
    metadata: dict[str, Any] = Field(default_factory=dict)


class SynthesisJob(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.QUEUED
    progress_message: str = "Queued"
    request: SynthesisRequest
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
    preview_url: str | None = None
    download_url: str | None = None
    output_available: bool = False
    artifact: AudioArtifact | None = None

    def transition(self, status: JobStatus, message: str) -> None:
        if self.status in {JobStatus.COMPLETED, JobStatus.FAILED}:
            raise ValidationError(
                "invalid_transition", "Completed jobs cannot transition again."
            )
        self.status = status
        self.progress_message = message
        self.updated_at = utcnow()

    def succeed(self, result: SynthesisResult) -> None:
        self.status = JobStatus.COMPLETED
        self.progress_message = "Completed"
        self.updated_at = utcnow()
        self.completed_at = utcnow()
        self.preview_url = result.artifact.preview_url
        self.download_url = result.artifact.download_url
        self.output_available = True
        self.artifact = result.artifact

    def fail(self, error_code: str, message: str) -> None:
        self.status = JobStatus.FAILED
        self.progress_message = "Failed"
        self.updated_at = utcnow()
        self.completed_at = utcnow()
        self.error_code = error_code
        self.error_message = message


class JobSummary(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    completed_at: datetime | None = None
    model: ModelId
    preview_url: str | None = None
    download_url: str | None = None


class BackendSynthesisOutput(BaseModel):
    wav_path: Path
    metadata: dict[str, Any] = Field(default_factory=dict)

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domain.models import JobStatus, ModelDescriptor, SynthesisJob, VoiceSample


class JobCreatedResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress_message: str
    model: str
    output_available: bool
    preview_url: str | None
    download_url: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None = None

    @classmethod
    def from_job(cls, job: SynthesisJob) -> "JobStatusResponse":
        return cls(
            job_id=job.job_id,
            status=job.status,
            progress_message=job.progress_message,
            model=job.request.model.value,
            output_available=job.output_available,
            preview_url=job.preview_url,
            download_url=job.download_url,
            error_code=job.error_code,
            error_message=job.error_message,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )


class ConfigResponse(BaseModel):
    app_title: str
    offline_mode: bool
    default_model: str
    max_input_length: int


class ModelsResponse(BaseModel):
    models: list[ModelDescriptor]


class VoiceSampleResponse(BaseModel):
    sample_id: str
    name: str
    transcript: str
    duration_seconds: float
    created_at: datetime
    updated_at: datetime
    audio_url: str

    @classmethod
    def from_sample(cls, sample: VoiceSample) -> "VoiceSampleResponse":
        return cls(
            sample_id=sample.sample_id,
            name=sample.name,
            transcript=sample.transcript,
            duration_seconds=sample.duration_seconds,
            created_at=sample.created_at,
            updated_at=sample.updated_at,
            audio_url=sample.audio_url or f"/api/voices/{sample.sample_id}/audio",
        )


class VoiceSampleUpdateRequest(BaseModel):
    name: str | None = None
    transcript: str | None = None

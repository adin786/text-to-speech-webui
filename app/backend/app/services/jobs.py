from __future__ import annotations

import logging
import threading
from pathlib import Path
from queue import Queue

from app.adapters.audio.ffmpeg import AudioProcessor
from app.adapters.storage.filesystem import ArtifactStore, JobStore
from app.core.config import Settings
from app.domain.errors import AppError, NotFoundError, ValidationError
from app.domain.models import (
    AppConfig,
    AudioArtifact,
    BackendSynthesisOutput,
    JobStatus,
    JobSummary,
    SynthesisJob,
    SynthesisRequest,
    SynthesisResult,
)
from app.services.models import ModelRegistryService

logger = logging.getLogger(__name__)


class JobService:
    def __init__(
        self,
        config: AppConfig,
        settings: Settings,
        model_registry: ModelRegistryService,
        job_store: JobStore,
        artifact_store: ArtifactStore,
        audio_processor: AudioProcessor,
    ) -> None:
        self.config = config
        self.settings = settings
        self.model_registry = model_registry
        self.job_store = job_store
        self.artifact_store = artifact_store
        self.audio_processor = audio_processor
        self.queue: Queue[str] = Queue()
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.started = False

    def start(self) -> None:
        if not self.started:
            self.worker.start()
            self.started = True

    def create_job(self, request: SynthesisRequest) -> SynthesisJob:
        if len(request.text) > self.config.max_input_length:
            raise ValidationError("text_too_long", f"Text must be <= {self.config.max_input_length} characters.")
        job = SynthesisJob(request=request)
        self.job_store.save_job(job)
        self.queue.put(job.job_id)
        return job

    def list_jobs(self) -> list[JobSummary]:
        jobs = self.job_store.list_jobs(limit=self.config.keep_history_limit)
        return [
            JobSummary(
                job_id=job.job_id,
                status=job.status,
                created_at=job.created_at,
                completed_at=job.completed_at,
                model=job.request.model,
                preview_url=job.preview_url,
                download_url=job.download_url,
            )
            for job in jobs
        ]

    def get_job(self, job_id: str) -> SynthesisJob:
        job = self.job_store.get_job(job_id)
        if not job:
            raise NotFoundError("job_not_found", f"Job {job_id} was not found.", status_code=404)
        return job

    def get_artifact_path(self, job_id: str, kind: str) -> Path:
        job = self.get_job(job_id)
        if not job.artifact:
            raise NotFoundError("artifact_not_found", f"Job {job_id} has no generated artifact.", status_code=404)
        if kind == "audio":
            return job.artifact.mp3_path
        raise NotFoundError("artifact_not_found", "Unsupported artifact.", status_code=404)

    def _worker_loop(self) -> None:
        while True:
            job_id = self.queue.get()
            try:
                self._process_job(job_id)
            finally:
                self.queue.task_done()

    def _process_job(self, job_id: str) -> None:
        job = self.get_job(job_id)
        try:
            job.transition(JobStatus.VALIDATING, "Validating request")
            self.job_store.save_job(job)
            backend = self.model_registry.require_backend(job.request.model)
            job.transition(JobStatus.RUNNING, f"Generating audio with {job.request.model.value}")
            self.job_store.save_job(job)
            wav_output = backend.synthesize_to_wav(job)
            job.transition(JobStatus.POST_PROCESSING, "Encoding MP3")
            self.job_store.save_job(job)
            result = self._finalize_artifacts(job, wav_output)
            job.succeed(result)
            self.job_store.save_job(job)
            logger.info(
                "job_completed",
                extra={
                    "job_id": job.job_id,
                    "model": job.request.model.value,
                },
            )
        except AppError as exc:
            job.fail(exc.error_code, exc.message)
            self.job_store.save_job(job)
            logger.error(
                "job_failed",
                extra={
                    "job_id": job.job_id,
                    "model": job.request.model.value,
                    "error_code": exc.error_code,
                },
            )
        except Exception as exc:  # pragma: no cover
            job.fail("runtime_error", str(exc))
            self.job_store.save_job(job)
            logger.exception("unexpected_job_failure", extra={"job_id": job.job_id})

    def _finalize_artifacts(self, job: SynthesisJob, backend_output: BackendSynthesisOutput) -> SynthesisResult:
        mp3_path = self.artifact_store.allocate_mp3_path(job.job_id)
        wav_path = self.audio_processor.normalize_wav(backend_output.wav_path)
        self.audio_processor.encode_mp3(wav_path, mp3_path)
        artifact = AudioArtifact(
            wav_path=wav_path,
            mp3_path=mp3_path,
            preview_url=f"/api/jobs/{job.job_id}/audio",
            download_url=f"/api/jobs/{job.job_id}/download",
            file_name=f"{job.job_id}.mp3",
            size_bytes=mp3_path.stat().st_size,
        )
        if not self.settings.preserve_wav and wav_path.exists():
            wav_path.unlink(missing_ok=True)
        return SynthesisResult(artifact=artifact, metadata=backend_output.metadata)

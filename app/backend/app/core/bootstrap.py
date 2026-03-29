from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.adapters.audio.ffmpeg import AudioProcessor
from app.adapters.storage.filesystem import ArtifactStore, JobStore, ModelStore
from app.adapters.tts.kokoro import KokoroBackend
from app.adapters.tts.qwen import QwenBackend
from app.core.config import Settings
from app.domain.models import AppConfig
from app.services.jobs import JobService
from app.services.models import ModelRegistryService


@dataclass
class AppContainer:
    config: AppConfig
    job_service: JobService
    model_service: ModelRegistryService


def ensure_runtime_directories(settings: Settings) -> None:
    for root in settings.runtime_roots:
        Path(root).mkdir(parents=True, exist_ok=True)


def build_container(settings: Settings) -> AppContainer:
    ensure_runtime_directories(settings)
    app_config = AppConfig(
        app_title=settings.app_title,
        offline_mode=settings.offline_mode,
        default_model=settings.default_model,
        max_input_length=settings.max_input_length,
        keep_history_limit=settings.keep_history_limit,
    )
    model_store = ModelStore(settings.model_root)
    job_store = JobStore(settings.jobs_root)
    artifact_store = ArtifactStore(settings.output_root)
    model_service = ModelRegistryService(
        config=app_config,
        backends=[
            KokoroBackend(settings=settings, model_store=model_store),
            QwenBackend(settings=settings, model_store=model_store),
        ],
    )
    audio_processor = AudioProcessor(
        ffmpeg_binary=settings.ffmpeg_binary,
        preserve_wav=settings.preserve_wav,
    )
    job_service = JobService(
        config=app_config,
        settings=settings,
        model_registry=model_service,
        job_store=job_store,
        artifact_store=artifact_store,
        audio_processor=audio_processor,
    )
    job_service.start()
    return AppContainer(
        config=app_config,
        job_service=job_service,
        model_service=model_service,
    )

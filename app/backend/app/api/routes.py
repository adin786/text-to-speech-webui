from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.schemas import (
    ConfigResponse,
    JobCreatedResponse,
    JobStatusResponse,
    ModelsResponse,
)
from app.core.dependencies import get_container
from app.domain.errors import AppError
from app.domain.models import SynthesisRequest

router = APIRouter()


def raise_http(exc: AppError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"error_code": exc.error_code, "message": exc.message},
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/config", response_model=ConfigResponse)
def config(container=Depends(get_container)) -> ConfigResponse:
    return ConfigResponse(
        app_title=container.config.app_title,
        offline_mode=container.config.offline_mode,
        default_model=container.config.default_model,
        max_input_length=container.config.max_input_length,
    )


@router.get("/models", response_model=ModelsResponse)
def models(container=Depends(get_container)) -> ModelsResponse:
    return ModelsResponse(models=container.model_service.list_models())


@router.get("/jobs")
def list_jobs(container=Depends(get_container)) -> list[dict]:
    return [job.model_dump(mode="json") for job in container.job_service.list_jobs()]


@router.post("/jobs", response_model=JobCreatedResponse)
def create_job(
    request: SynthesisRequest, container=Depends(get_container)
) -> JobCreatedResponse:
    try:
        job = container.job_service.create_job(request)
        return JobCreatedResponse(
            job_id=job.job_id, status=job.status, created_at=job.created_at
        )
    except AppError as exc:
        raise_http(exc)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, container=Depends(get_container)) -> JobStatusResponse:
    try:
        return JobStatusResponse.from_job(container.job_service.get_job(job_id))
    except AppError as exc:
        raise_http(exc)


@router.get("/jobs/{job_id}/audio")
def get_audio(job_id: str, container=Depends(get_container)) -> FileResponse:
    try:
        return FileResponse(
            container.job_service.get_artifact_path(job_id, "audio"),
            media_type="audio/mpeg",
        )
    except AppError as exc:
        raise_http(exc)


@router.get("/jobs/{job_id}/download")
def download_audio(job_id: str, container=Depends(get_container)) -> FileResponse:
    try:
        path = container.job_service.get_artifact_path(job_id, "audio")
        return FileResponse(path, media_type="audio/mpeg", filename=path.name)
    except AppError as exc:
        raise_http(exc)

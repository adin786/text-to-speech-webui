from __future__ import annotations

import asyncio
import time
from pathlib import Path

import httpx
import pytest

from app.core.config import get_settings
from app.main import create_app


async def wait_for_completion(client: httpx.AsyncClient, job_id: str) -> dict:
    deadline = time.time() + 10
    while time.time() < deadline:
        response = await client.get(f"/api/jobs/{job_id}")
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        await asyncio.sleep(0.1)
    raise AssertionError("Job did not complete in time.")


@pytest.fixture(autouse=True)
def isolated_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_ROOT", str(tmp_path / "models"))
    monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path / "output"))
    monkeypatch.setenv("JOBS_ROOT", str(tmp_path / "jobs"))
    monkeypatch.setenv("LOGS_ROOT", str(tmp_path / "logs"))
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_health_endpoint() -> None:
    async def run() -> None:
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    asyncio.run(run())


def test_job_generation_flow() -> None:
    async def run() -> None:
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            create = await client.post(
                "/api/jobs",
                json={"text": "Hello world", "model": "kokoro", "speed": 1.0, "output_format": "mp3"},
            )
            assert create.status_code == 200
            payload = create.json()
            result = await wait_for_completion(client, payload["job_id"])
            assert result["status"] == "completed"
            audio = await client.get(result["download_url"])
            assert audio.status_code == 200
            assert audio.headers["content-type"].startswith("audio/mpeg")
            assert len(audio.content) > 0

    asyncio.run(run())


def test_models_endpoint_marks_qwen_unavailable_without_model_dir() -> None:
    async def run() -> None:
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/models")
            assert response.status_code == 200
            models = {model["id"]: model for model in response.json()["models"]}
            assert models["kokoro"]["available"] is True
            assert models["qwen3_0_6b"]["available"] is False

    asyncio.run(run())


def test_create_job_returns_useful_error_when_model_assets_are_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "false")
    get_settings.cache_clear()

    async def run() -> None:
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/jobs",
                json={"text": "Hello world", "model": "kokoro", "speed": 1.0, "output_format": "mp3"},
            )
            assert response.status_code == 409
            assert response.json()["detail"]["error_code"] == "model_unavailable"
            assert "missing" in response.json()["detail"]["message"].lower()

    try:
        asyncio.run(run())
    finally:
        get_settings.cache_clear()

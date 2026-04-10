from __future__ import annotations

import asyncio
import io
import shutil
import time
from pathlib import Path
import wave

import httpx
import pytest

from app.adapters.audio.ffmpeg import AudioProcessor
from app.adapters.storage.filesystem import JobStore
from app.adapters.tts.kokoro import KokoroBackend
from app.domain.errors import RuntimeFailure
from app.domain.models import JobStatus, SynthesisJob, SynthesisRequest
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


def sample_wav_bytes() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * 16000)
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def isolated_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_ROOT", str(tmp_path / "models"))
    monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path / "output"))
    monkeypatch.setenv("JOBS_ROOT", str(tmp_path / "jobs"))
    monkeypatch.setenv("VOICE_SAMPLES_ROOT", str(tmp_path / "voices"))
    monkeypatch.setenv("LOGS_ROOT", str(tmp_path / "logs"))
    monkeypatch.setenv("DEMO_MODE", "true")

    def fake_encode_mp3(self: AudioProcessor, wav_path: Path, mp3_path: Path) -> None:
        mp3_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(wav_path, mp3_path)

    def fake_normalize_reference_audio(
        self: AudioProcessor, source_path: Path, wav_path: Path
    ) -> Path:
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, wav_path)
        return wav_path

    monkeypatch.setattr(AudioProcessor, "encode_mp3", fake_encode_mp3)
    monkeypatch.setattr(
        AudioProcessor, "normalize_reference_audio", fake_normalize_reference_audio
    )
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_health_endpoint() -> None:
    async def run() -> None:
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            response = await client.get("/api/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    asyncio.run(run())


def test_config_endpoint_exposes_default_job_timeout() -> None:
    async def run() -> None:
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            response = await client.get("/api/config")
            assert response.status_code == 200
            assert response.json()["job_timeout_seconds"] == 120

    asyncio.run(run())


def test_job_generation_flow() -> None:
    async def run() -> None:
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            create = await client.post(
                "/api/jobs",
                json={
                    "text": "Hello world",
                    "model": "kokoro",
                    "speed": 1.0,
                    "output_format": "mp3",
                },
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


def test_models_endpoint_keeps_qwen_available_in_demo_mode() -> None:
    async def run() -> None:
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            response = await client.get("/api/models")
            assert response.status_code == 200
            models = {model["id"]: model for model in response.json()["models"]}
            assert models["kokoro"]["available"] is True
            assert models["qwen3_0_6b"]["available"] is True

    asyncio.run(run())


def test_job_fails_when_synthesis_exceeds_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def slow_synthesize(self, job):  # noqa: ANN001, ANN202
        time.sleep(2)
        raise RuntimeFailure("should_not_finish", "Timed out job should not complete.")

    monkeypatch.setattr(KokoroBackend, "synthesize_to_wav", slow_synthesize)

    async def run() -> None:
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            create = await client.post(
                "/api/jobs",
                json={
                    "text": "Hello world",
                    "model": "kokoro",
                    "speed": 1.0,
                    "timeout_seconds": 1,
                    "output_format": "mp3",
                },
            )
            assert create.status_code == 200
            payload = create.json()
            result = await wait_for_completion(client, payload["job_id"])
            assert result["status"] == "failed"
            assert result["error_code"] == "job_timeout"
            assert "timeout" in result["error_message"].lower()

    try:
        asyncio.run(run())
    finally:
        time.sleep(2.1)


def test_startup_recovers_incomplete_jobs() -> None:
    settings = get_settings()
    store = JobStore(settings.jobs_root)

    running_job = SynthesisJob(
        request=SynthesisRequest(text="stuck", model="kokoro"),
        status=JobStatus.RUNNING,
        progress_message="Generating audio with kokoro",
    )
    queued_job = SynthesisJob(
        request=SynthesisRequest(text="queued", model="kokoro"),
        status=JobStatus.QUEUED,
        progress_message="Queued",
    )
    store.save_job(running_job)
    store.save_job(queued_job)

    app = create_app()
    transport = httpx.ASGITransport(app=app)

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            running = await client.get(f"/api/jobs/{running_job.job_id}")
            queued = await client.get(f"/api/jobs/{queued_job.job_id}")

            assert running.status_code == 200
            assert queued.status_code == 200

            running_payload = running.json()
            queued_payload = queued.json()

            assert running_payload["status"] == "failed"
            assert running_payload["error_code"] == "job_interrupted"
            assert "backend restart" in running_payload["error_message"].lower()

            assert queued_payload["status"] in {
                "queued",
                "validating",
                "running",
                "completed",
            }

    asyncio.run(run())


def test_voice_sample_crud_flow() -> None:
    async def run() -> None:
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            create = await client.post(
                "/api/voices",
                data={
                    "name": "Desk mic",
                    "transcript": "Hello there this is my saved voice sample.",
                },
                files={"audio": ("sample.wav", sample_wav_bytes(), "audio/wav")},
            )
            assert create.status_code == 200
            created = create.json()
            assert created["name"] == "Desk mic"
            assert created["audio_url"].startswith("/api/voices/")

            listing = await client.get("/api/voices")
            assert listing.status_code == 200
            assert len(listing.json()) == 1

            update = await client.patch(
                f"/api/voices/{created['sample_id']}",
                json={"name": "Desk mic v2", "transcript": "Updated transcript"},
            )
            assert update.status_code == 200
            assert update.json()["name"] == "Desk mic v2"

            audio = await client.get(update.json()["audio_url"])
            assert audio.status_code == 200
            assert audio.headers["content-type"].startswith("audio/wav")

            remove = await client.delete(f"/api/voices/{created['sample_id']}")
            assert remove.status_code == 204

            listing_after_delete = await client.get("/api/voices")
            assert listing_after_delete.status_code == 200
            assert listing_after_delete.json() == []

    asyncio.run(run())


def test_qwen_job_with_missing_saved_voice_returns_useful_error() -> None:
    async def run() -> None:
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            response = await client.post(
                "/api/jobs",
                json={
                    "text": "Hello world",
                    "model": "qwen3_0_6b",
                    "saved_voice_id": "missing-sample",
                    "speed": 1.0,
                    "output_format": "mp3",
                },
            )
            assert response.status_code == 404
            assert response.json()["detail"]["error_code"] == "voice_sample_not_found"

    asyncio.run(run())


def test_create_job_returns_useful_error_when_model_assets_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEMO_MODE", "false")
    get_settings.cache_clear()

    async def run() -> None:
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            response = await client.post(
                "/api/jobs",
                json={
                    "text": "Hello world",
                    "model": "kokoro",
                    "speed": 1.0,
                    "output_format": "mp3",
                },
            )
            assert response.status_code == 409
            assert response.json()["detail"]["error_code"] == "model_unavailable"
            assert "missing" in response.json()["detail"]["message"].lower()

    try:
        asyncio.run(run())
    finally:
        get_settings.cache_clear()

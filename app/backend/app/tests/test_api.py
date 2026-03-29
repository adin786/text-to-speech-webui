from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def wait_for_completion(client: TestClient, job_id: str) -> dict:
    deadline = time.time() + 10
    while time.time() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.1)
    raise AssertionError("Job did not complete in time.")


def test_health_endpoint() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_job_generation_flow() -> None:
    app = create_app()
    with TestClient(app) as client:
        create = client.post(
            "/api/jobs",
            json={"text": "Hello world", "model": "kokoro", "speed": 1.0, "output_format": "mp3"},
        )
        assert create.status_code == 200
        payload = create.json()
        result = wait_for_completion(client, payload["job_id"])
        assert result["status"] == "completed"
        audio = client.get(result["download_url"])
        assert audio.status_code == 200
        assert audio.headers["content-type"].startswith("audio/mpeg")
        assert len(audio.content) > 0


def test_models_endpoint_marks_qwen_unavailable_without_model_dir() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/models")
        assert response.status_code == 200
        models = {model["id"]: model for model in response.json()["models"]}
        assert models["kokoro"]["available"] is True
        assert models["qwen3_0_6b"]["available"] is False

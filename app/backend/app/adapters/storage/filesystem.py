from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import SynthesisJob


class ModelStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def model_dir(self, model_name: str) -> Path:
        return self.root / model_name


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def allocate_mp3_path(self, job_id: str) -> Path:
        return self.root / f"{job_id}.mp3"


class JobStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        return self.root / f"{job_id}.json"

    def save_job(self, job: SynthesisJob) -> None:
        self._path(job.job_id).write_text(job.model_dump_json(indent=2, exclude_none=True))

    def get_job(self, job_id: str) -> SynthesisJob | None:
        path = self._path(job_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text())
        return SynthesisJob.model_validate(payload)

    def list_jobs(self, limit: int) -> list[SynthesisJob]:
        jobs = []
        for path in sorted(self.root.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            payload = json.loads(path.read_text())
            jobs.append(SynthesisJob.model_validate(payload))
        return jobs[:limit]

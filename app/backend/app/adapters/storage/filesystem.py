from __future__ import annotations

import json
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile
from uuid import uuid4

from app.domain.models import SynthesisJob, VoiceSample


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
        path = self._path(job.job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            handle.write(job.model_dump_json(indent=2, exclude_none=True))
            temp_path = Path(handle.name)
        temp_path.replace(path)

    def get_job(self, job_id: str) -> SynthesisJob | None:
        path = self._path(job_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return SynthesisJob.model_validate(payload)

    def list_jobs(self, limit: int) -> list[SynthesisJob]:
        jobs = []
        for path in sorted(
            self.root.glob("*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        ):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                jobs.append(SynthesisJob.model_validate(payload))
            except (OSError, json.JSONDecodeError, ValueError):
                continue
        return jobs[:limit]


class VoiceSampleStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def sample_dir(self, sample_id: str) -> Path:
        return self.root / sample_id

    def audio_path(self, sample_id: str) -> Path:
        return self.sample_dir(sample_id) / "reference.wav"

    def _meta_path(self, sample_id: str) -> Path:
        return self.sample_dir(sample_id) / "metadata.json"

    def create_sample_id(self) -> str:
        return str(uuid4())

    def save_sample(self, sample: VoiceSample) -> None:
        path = self._meta_path(sample.sample_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            handle.write(sample.model_dump_json(indent=2, exclude_none=True))
            temp_path = Path(handle.name)
        temp_path.replace(path)

    def store_audio_file(self, sample_id: str, source_path: Path) -> Path:
        destination = self.audio_path(sample_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        source_path.replace(destination)
        return destination

    def get_sample(self, sample_id: str) -> VoiceSample | None:
        path = self._meta_path(sample_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return VoiceSample.model_validate(payload)

    def list_samples(self) -> list[VoiceSample]:
        samples = []
        for path in sorted(
            self.root.glob("*/metadata.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        ):
            payload = json.loads(path.read_text(encoding="utf-8"))
            samples.append(VoiceSample.model_validate(payload))
        return samples

    def delete_sample(self, sample_id: str) -> None:
        shutil.rmtree(self.sample_dir(sample_id), ignore_errors=True)

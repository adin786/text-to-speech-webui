from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    app_title: str = "Text to Speech WebUI"
    api_prefix: str = "/api"
    offline_mode: bool = True
    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    model_root: Path = Path("runtime/models")
    output_root: Path = Path("runtime/output")
    jobs_root: Path = Path("runtime/data/jobs")
    logs_root: Path = Path("runtime/logs")
    frontend_dist: Path = Path("app/frontend/dist")
    default_model: str = "kokoro"
    enable_kokoro: bool = True
    enable_qwen: bool = True
    max_input_length: int = 1_000
    ffmpeg_binary: str = "ffmpeg"
    job_timeout_seconds: int = 120
    preserve_wav: bool = False
    keep_history_limit: int = 25
    qwen_enabled_in_ui: bool = True
    environment: str = "development"
    demo_mode: bool = True
    qwen_model_dir_name: str = "qwen3_0_6b"
    kokoro_model_dir_name: str = "kokoro"
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"])

    @property
    def runtime_roots(self) -> list[Path]:
        return [self.model_root, self.output_root, self.jobs_root, self.logs_root]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

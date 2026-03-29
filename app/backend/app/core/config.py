from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

BACKEND_APP_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BACKEND_APP_DIR.parent
REPO_ROOT = BACKEND_DIR.parent.parent


class Settings(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    app_title: str = "Text to Speech WebUI"
    api_prefix: str = "/api"
    offline_mode: bool = True
    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    model_root: Path = REPO_ROOT / "runtime/models"
    output_root: Path = REPO_ROOT / "runtime/output"
    jobs_root: Path = REPO_ROOT / "runtime/data/jobs"
    logs_root: Path = REPO_ROOT / "runtime/logs"
    frontend_dist: Path = REPO_ROOT / "app/frontend/dist"
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
    return Settings(
        app_title=os.getenv("APP_TITLE", Settings.model_fields["app_title"].default),
        api_prefix=os.getenv("API_PREFIX", Settings.model_fields["api_prefix"].default),
        offline_mode=os.getenv("OFFLINE_MODE", "true").lower() == "true",
        bind_host=os.getenv("BIND_HOST", Settings.model_fields["bind_host"].default),
        bind_port=int(os.getenv("BIND_PORT", Settings.model_fields["bind_port"].default)),
        model_root=Path(os.getenv("MODEL_ROOT", str(Settings.model_fields["model_root"].default))),
        output_root=Path(os.getenv("OUTPUT_ROOT", str(Settings.model_fields["output_root"].default))),
        jobs_root=Path(os.getenv("JOBS_ROOT", str(Settings.model_fields["jobs_root"].default))),
        logs_root=Path(os.getenv("LOGS_ROOT", str(Settings.model_fields["logs_root"].default))),
        frontend_dist=Path(os.getenv("FRONTEND_DIST", str(Settings.model_fields["frontend_dist"].default))),
        default_model=os.getenv("DEFAULT_MODEL", Settings.model_fields["default_model"].default),
        enable_kokoro=os.getenv("ENABLE_KOKORO", "true").lower() == "true",
        enable_qwen=os.getenv("ENABLE_QWEN", "true").lower() == "true",
        max_input_length=int(os.getenv("MAX_INPUT_LENGTH", Settings.model_fields["max_input_length"].default)),
        ffmpeg_binary=os.getenv("FFMPEG_BINARY", Settings.model_fields["ffmpeg_binary"].default),
        job_timeout_seconds=int(
            os.getenv("JOB_TIMEOUT_SECONDS", Settings.model_fields["job_timeout_seconds"].default),
        ),
        preserve_wav=os.getenv("PRESERVE_WAV", "false").lower() == "true",
        keep_history_limit=int(
            os.getenv("KEEP_HISTORY_LIMIT", Settings.model_fields["keep_history_limit"].default),
        ),
        qwen_enabled_in_ui=os.getenv("QWEN_ENABLED_IN_UI", "true").lower() == "true",
        environment=os.getenv("ENVIRONMENT", Settings.model_fields["environment"].default),
        demo_mode=os.getenv("DEMO_MODE", "true").lower() == "true",
        qwen_model_dir_name=os.getenv(
            "QWEN_MODEL_DIR_NAME",
            Settings.model_fields["qwen_model_dir_name"].default,
        ),
        kokoro_model_dir_name=os.getenv(
            "KOKORO_MODEL_DIR_NAME",
            Settings.model_fields["kokoro_model_dir_name"].default,
        ),
    )

from __future__ import annotations

from app.adapters.tts.base import TTSBackend
from app.domain.errors import AvailabilityError
from app.domain.models import AppConfig, ModelDescriptor, ModelId


class ModelRegistryService:
    def __init__(self, config: AppConfig, backends: list[TTSBackend]) -> None:
        self.config = config
        self.backends = {backend.model_id: backend for backend in backends}

    def list_models(self) -> list[ModelDescriptor]:
        return [backend.describe() for backend in self.backends.values()]

    def get_model(self, model_id: ModelId) -> ModelDescriptor:
        backend = self.backends[model_id]
        return backend.describe()

    def require_backend(self, model_id: ModelId) -> TTSBackend:
        backend = self.backends[model_id]
        descriptor = backend.describe()
        if not descriptor.enabled:
            raise AvailabilityError(
                "model_disabled", f"Model {model_id} is disabled.", status_code=400
            )
        if not descriptor.available:
            raise AvailabilityError(
                "model_unavailable",
                descriptor.notes or f"Model {model_id} is unavailable.",
                status_code=409,
            )
        return backend

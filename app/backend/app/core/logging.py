from __future__ import annotations

import json
import logging
from pathlib import Path


def configure_logging(logs_root: Path) -> None:
    logs_root.mkdir(parents=True, exist_ok=True)
    logfile = logs_root / "app.log"

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            payload = {
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            if hasattr(record, "job_id"):
                payload["job_id"] = getattr(record, "job_id")
            if hasattr(record, "model"):
                payload["model"] = getattr(record, "model")
            if hasattr(record, "error_code"):
                payload["error_code"] = getattr(record, "error_code")
            return json.dumps(payload)

    handler = logging.FileHandler(logfile)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

"""Append-only JSONL audit log (one file per headless session).

Implements the auditability invariant (SPEC S4): every spawn + completion is
recorded with git state before/after, duration, and exit status.
"""
import json
import os
from datetime import datetime, timezone

from . import config


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs():
    os.makedirs(config.HEADLESS_LOG_DIR, exist_ok=True)


def new_session_id(label: str) -> str:
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{label}"


def log_path(session_id: str) -> str:
    return os.path.join(config.HEADLESS_LOG_DIR, f"{session_id}.jsonl")


def write_record(session_id: str, record: dict):
    with open(log_path(session_id), "a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")

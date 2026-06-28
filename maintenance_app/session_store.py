"""In-memory session store for uploaded / active datasets."""

import time
import uuid
from typing import Any

_sessions: dict[str, dict[str, Any]] = {}
DEFAULT_SESSION = "default"


def create_session(dataset: dict, source: str = "upload") -> str:
    sid = uuid.uuid4().hex
    _sessions[sid] = {
        "data": dataset,
        "source": source,
        "filename": dataset.get("source_file", source),
        "created": time.time(),
    }
    return sid


def set_default_session(dataset: dict, source: str = "X.md") -> None:
    _sessions[DEFAULT_SESSION] = {
        "data": dataset,
        "source": source,
        "filename": source,
        "created": time.time(),
    }


def get_session(session_id: str | None) -> dict | None:
    if not session_id:
        return _sessions.get(DEFAULT_SESSION)
    return _sessions.get(session_id)


def get_dataset(session_id: str | None = None) -> dict:
    entry = get_session(session_id)
    if not entry:
        raise KeyError("Session not found. Upload a file or reload default data.")
    return entry["data"]


def session_info(session_id: str | None = None) -> dict:
    entry = get_session(session_id)
    if not entry:
        return {"active": False}
    data = entry["data"]
    return {
        "active": True,
        "session_id": session_id or DEFAULT_SESSION,
        "source": entry["source"],
        "filename": entry.get("filename"),
        "months": data.get("months_parsed", 0),
        "date_range": data.get("date_range"),
    }

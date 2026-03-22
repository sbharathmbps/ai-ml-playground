"""
In-memory session store.
Each session tracks conversation history, last query results,
active cart ID, and whether we are awaiting order confirmation.

In production replace the dict store with Redis.
"""

import uuid
import logging
from threading import Lock
from config import MAX_HISTORY_TURNS

logger = logging.getLogger(__name__)

_sessions: dict[str, dict] = {}
_lock = Lock()


def _empty_session(session_id: str) -> dict:
    return {
        "session_id":           session_id,
        "history":              [],   # [{"role": "user"|"assistant", "content": str}]
        "last_results":         [],   # last DB query result rows (list of dicts)
        "cart_id":              None, # set once a cart row is created
        "awaiting_confirmation": False,
        "pending_order_summary": None,  # billing dict shown before confirm
    }


def get_or_create_session(session_id: str | None = None) -> dict:
    with _lock:
        if session_id is None or session_id not in _sessions:
            sid = session_id or str(uuid.uuid4())
            _sessions[sid] = _empty_session(sid)
            logger.info(f"New session created: {sid}")
            return _sessions[sid]
        return _sessions[session_id]


def get_session(session_id: str) -> dict | None:
    return _sessions.get(session_id)


def update_session(session_id: str, **kwargs):
    """Update arbitrary fields on a session."""
    with _lock:
        if session_id not in _sessions:
            return
        _sessions[session_id].update(kwargs)


def append_history(session_id: str, role: str, content: str):
    """Add a turn to conversation history, trimming to MAX_HISTORY_TURNS."""
    with _lock:
        sess = _sessions.get(session_id)
        if not sess:
            return
        sess["history"].append({"role": role, "content": content})
        # keep only the last N turns (2 entries per turn = user + assistant)
        if len(sess["history"]) > MAX_HISTORY_TURNS * 2:
            sess["history"] = sess["history"][-(MAX_HISTORY_TURNS * 2):]


def clear_session(session_id: str):
    with _lock:
        if session_id in _sessions:
            del _sessions[session_id]

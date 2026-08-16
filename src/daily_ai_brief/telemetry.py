# SPDX-License-Identifier: MIT
"""Anonymous usage telemetry: identity, environment signals, and transport to
the gateway (https://daily-ai-brief.builditwithai.xyz/e). Opt-out and privacy: see README."""

from __future__ import annotations

import atexit
import contextvars
import json
import os
import platform
import re
import sys
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

GATEWAY_URL = "https://daily-ai-brief.builditwithai.xyz/e"
SCHEMA_VERSION = 2
SERVER_NAME = "daily-ai-brief"

STATUS_OK = {"success", "warning", "cancelled"}
STATUS_ERR = {"error", "exception"}
ERROR_CATEGORIES = {
    "APIError", "ValidationError", "SchemaHallucination", "IAMError",
    "TimeoutError", "RateLimitError", "NotFoundError", "SourceUnavailable",
    "MissingApiKey", "InternalError", "Cancelled", "InitError"
}

try:
    import importlib.metadata
    MCP_SERVER_VERSION = importlib.metadata.version("daily-ai-brief")
except Exception:
    MCP_SERVER_VERSION = "0.1.0"


def _telemetry_disabled() -> bool:
    if os.getenv("DAILY_AI_BRIEF_TELEMETRY", "true").lower() in ("false", "0", "off"):
        return True
    for var in ("DISABLE_TELEMETRY", "DO_NOT_TRACK", "NO_TELEMETRY"):
        if os.getenv(var, "").lower() in ("1", "true", "yes", "on"):
            return True
    return False


TELEMETRY_DISABLED = _telemetry_disabled()
INTERNAL_RUN = os.getenv("DAILY_AI_BRIEF_INTERNAL", "").lower() in ("1", "true", "yes")


def _init_anonymous_identity():
    try:
        config_dir = Path.home() / ".daily_ai_brief"
        id_file = config_dir / "installation_id"

        if TELEMETRY_DISABLED:
            if id_file.exists():
                return id_file.read_text(encoding="utf-8").strip(), False
            return f"anon_{uuid.uuid4()}", False

        if id_file.exists():
            return id_file.read_text(encoding="utf-8").strip(), False

        config_dir.mkdir(parents=True, exist_ok=True)
        new_id = f"inst_{uuid.uuid4()}"
        id_file.write_text(new_id, encoding="utf-8")
        return new_id, True
    except Exception:
        return f"anon_{uuid.uuid4()}", False


DISTINCT_ID, IS_FIRST_INSTALL = _init_anonymous_identity()
SESSION_ID = f"sess_{uuid.uuid4()}"


def _get_env_metadata() -> Dict[str, Any]:
    tz_offset = time.strftime("%z")
    formatted_tz = f"{tz_offset[:3]}:{tz_offset[3:]}" if len(tz_offset) == 5 else "+00:00"

    in_venv = sys.prefix != sys.base_prefix or bool(os.getenv("VIRTUAL_ENV")) or bool(os.getenv("CONDA_PREFIX"))

    run_context = "cli"
    agent_name = "unknown"
    if os.getenv("CLAUDE_CODE") or os.getenv("CLAUDE_PROJECT_DIR"):
        run_context = "claude_code"
        agent_name = "claude"
    elif os.getenv("CURSOR_TRACE") or os.getenv("CURSOR_SESSION"):
        run_context = "cursor"
        agent_name = "cursor"
    elif os.getenv("VSCODE_PID"):
        run_context = "vscode"
        agent_name = "copilot"
    elif os.getenv("ANTIGRAVITY_SESSION") or os.getenv("GEMINI_CLI"):
        run_context = "antigravity"
        agent_name = "antigravity"

    return {
        "schema_version": SCHEMA_VERSION,
        "mcp_server_name": SERVER_NAME,
        "mcp_server_version": MCP_SERVER_VERSION,
        "$os": platform.system(),
        "python_version": platform.python_version(),
        "cpu_arch": platform.machine(),
        "in_virtual_env": in_venv,
        "timezone_offset": formatted_tz,
        "run_context": run_context,
        "agent_name": agent_name,
        "discovery_channel": "direct",
        "install_source": "uvx" if "uv" in sys.executable else "pip",
        "session_id": SESSION_ID,
        "has_ever_worked": True,
        "mcp_client_name": run_context,
        "mcp_client_version": "unknown",
        "mcp_protocol_version": "2026-07-28",
        "client_capabilities": {},
        "traceparent": "",
        "trace_id": "",
        "span_id": "",
        "$process_person_profile": False,
    }


_EVENT_QUEUE = []
_QUEUE_LOCK = threading.Lock()
_WORKER_THREAD: Optional[threading.Thread] = None
_SHUTDOWN = threading.Event()


def _flush_queue():
    while not _SHUTDOWN.is_set():
        batch = []
        with _QUEUE_LOCK:
            if _EVENT_QUEUE:
                batch = _EVENT_QUEUE[:]
                _EVENT_QUEUE.clear()
        if batch:
            for event in batch:
                _send_event_sync(event)
        time.sleep(0.5)


def _send_event_sync(payload: Dict[str, Any]):
    if TELEMETRY_DISABLED:
        return
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            GATEWAY_URL,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": f"daily-ai-brief-telemetry/{MCP_SERVER_VERSION}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            pass
    except Exception:
        pass


def _ensure_worker():
    global _WORKER_THREAD
    if _WORKER_THREAD is None or not _WORKER_THREAD.is_alive():
        _WORKER_THREAD = threading.Thread(target=_flush_queue, daemon=True)
        _WORKER_THREAD.start()


def track_event(event_name: str, properties: Optional[Dict[str, Any]] = None):
    if TELEMETRY_DISABLED:
        return

    props = _get_env_metadata()
    if properties:
        props.update(properties)
    if INTERNAL_RUN:
        props["internal_run"] = True

    payload = {
        "event": event_name,
        "distinct_id": DISTINCT_ID,
        "properties": props,
    }

    with _QUEUE_LOCK:
        _EVENT_QUEUE.append(payload)
    _ensure_worker()


def track_tool_call(
    tool_name: str,
    duration_ms: float,
    status: str = "success",
    error_category: Optional[str] = None,
    error_message: Optional[str] = None,
    custom_props: Optional[Dict[str, Any]] = None,
):
    props = {
        "tool_name": tool_name,
        "duration_ms": duration_ms,
        "status": status if status in STATUS_OK | STATUS_ERR else "error",
    }
    if error_category:
        props["error_category"] = error_category if error_category in ERROR_CATEGORIES else "InternalError"
    if error_message:
        props["error_message"] = str(error_message)[:250]
    if custom_props:
        props.update(custom_props)

    track_event("tool_executed", props)


def flush_and_close():
    _SHUTDOWN.set()
    batch = []
    with _QUEUE_LOCK:
        batch = _EVENT_QUEUE[:]
        _EVENT_QUEUE.clear()
    for event in batch:
        _send_event_sync(event)


atexit.register(flush_and_close)

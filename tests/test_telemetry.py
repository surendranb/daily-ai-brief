"""Schema v2 Telemetry contract tests for daily-ai-brief."""

import pytest
from daily_ai_brief.telemetry import (
    ERROR_CATEGORIES,
    SCHEMA_VERSION,
    SERVER_NAME,
    STATUS_ERR,
    STATUS_OK,
    _get_env_metadata,
)

SCHEMA_V2_REQUIRED_PROPS = {
    "schema_version",
    "mcp_server_name",
    "mcp_server_version",
    "$os",
    "python_version",
    "cpu_arch",
    "in_virtual_env",
    "timezone_offset",
    "run_context",
    "agent_name",
    "discovery_channel",
    "install_source",
    "session_id",
    "has_ever_worked",
    "mcp_client_name",
    "mcp_client_version",
    "mcp_protocol_version",
    "client_capabilities",
    "traceparent",
    "trace_id",
    "span_id",
    "$process_person_profile",
}


def test_schema_v2_envelope_compliance():
    metadata = _get_env_metadata()
    missing = SCHEMA_V2_REQUIRED_PROPS - set(metadata.keys())
    assert not missing, f"Missing Schema v2 properties: {missing}"
    assert metadata["schema_version"] == 2
    assert metadata["mcp_server_name"] == "daily-ai-brief"
    assert metadata["$process_person_profile"] is False


def test_error_categories():
    assert "APIError" in ERROR_CATEGORIES
    assert "ValidationError" in ERROR_CATEGORIES
    assert "TimeoutError" in ERROR_CATEGORIES
    assert "SourceUnavailable" in ERROR_CATEGORIES


def test_track_tool_call_v2_properties(monkeypatch):
    from daily_ai_brief import telemetry
    captured = []
    monkeypatch.setattr(telemetry, "track_event", lambda ev, props: captured.append((ev, props)))
    
    telemetry.track_tool_call(
        tool_name="get_daily_ai_brief",
        duration_ms=145.8,
        status="success",
        rows_returned=12,
        result_chars=1024,
        intent="Summarize daily AI releases",
        custom_props={"areas_count": 4}
    )
    
    assert len(captured) == 1
    ev, props = captured[0]
    assert ev == "tool_executed"
    assert props["tool_name"] == "get_daily_ai_brief"
    assert props["status"] == "success"
    assert props["latency_ms"] == 145
    assert props["duration_ms"] == 145
    assert props["rows_returned"] == 12
    assert props["result_chars"] == 1024
    assert props["intent"] == "Summarize daily AI releases"
    assert props["areas_count"] == 4


def test_classify_exception_and_error_capture(monkeypatch):
    from daily_ai_brief import telemetry
    from daily_ai_brief.telemetry import classify_exception
    
    assert classify_exception(ValueError("Invalid parameter")) == "ValidationError"
    assert classify_exception(TimeoutError("Fetch timed out")) == "TimeoutError"
    assert classify_exception(KeyError("Resource not found 404")) == "NotFoundError"
    assert classify_exception(PermissionError("401 Unauthorized API key")) == "IAMError"
    assert classify_exception(Exception("429 Too Many Requests")) == "RateLimitError"
    assert classify_exception(RuntimeError("503 Service Unavailable")) == "SourceUnavailable"
    
    captured = []
    monkeypatch.setattr(telemetry, "track_event", lambda ev, props: captured.append((ev, props)))
    
    telemetry.track_tool_call(
        tool_name="get_arxiv_breakthroughs",
        duration_ms=88.0,
        status="error",
        error_category=classify_exception(TimeoutError("arXiv timeout")),
        error_message="arXiv timeout"
    )
    
    assert len(captured) == 1
    ev, props = captured[0]
    assert ev == "tool_executed"
    assert props["status"] == "error"
    assert props["error_category"] == "TimeoutError"
    assert props["error_message"] == "arXiv timeout"


"""Unit tests for check_for_updates tool, get_upgrade_nudge, and cache throttling."""

import json
import time
from unittest.mock import MagicMock, patch

from daily_ai_brief.server import (
    _FLEET_CACHE_FILE,
    _append_upgrade_nudge,
    _parse_version,
    check_for_updates,
    check_server_update,
    get_upgrade_nudge,
    skills_list,
)


def test_parse_version():
    assert _parse_version("0.1.4") == (0, 1, 4)
    assert _parse_version("v0.1.4") == (0, 1, 4)
    assert _parse_version("0.2.0") > _parse_version("0.1.4")
    assert _parse_version("0.1.4") > _parse_version("0.1.3")
    assert _parse_version("0.1.10") > _parse_version("0.1.4")
    assert _parse_version("unknown") == (0,)
    assert _parse_version("") == (0,)


def test_check_server_update_update_available(tmp_path):
    mock_pypi_data = json.dumps({"info": {"version": "0.2.0"}}).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_pypi_data
    mock_resp.__enter__.return_value = mock_resp

    test_cache = tmp_path / "mcp_fleet_updates.json"
    with patch("daily_ai_brief.server._FLEET_CACHE_FILE", test_cache), \
         patch("urllib.request.urlopen", return_value=mock_resp):
        res = check_server_update("daily-ai-brief", "0.1.4", force_check=True)

        assert res["server"] == "daily-ai-brief"
        assert res["current_version"] == "0.1.4"
        assert res["latest_version"] == "0.2.0"
        assert res["update_available"] is True
        assert res["upgrade_command"] == "uvx --refresh daily-ai-brief"
        assert "Inform the user to run 'uvx --refresh daily-ai-brief' to update." in res["message"]
        assert "Do NOT attempt to run this command yourself in this session." in res["message"]


def test_check_server_update_up_to_date(tmp_path):
    mock_pypi_data = json.dumps({"info": {"version": "0.1.4"}}).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_pypi_data
    mock_resp.__enter__.return_value = mock_resp

    test_cache = tmp_path / "mcp_fleet_updates.json"
    with patch("daily_ai_brief.server._FLEET_CACHE_FILE", test_cache), \
         patch("urllib.request.urlopen", return_value=mock_resp):
        res = check_server_update("daily-ai-brief", "0.1.4", force_check=True)

        assert res["update_available"] is False
        assert res["upgrade_command"] is None
        assert res["message"] == "daily-ai-brief is up to date (v0.1.4)."


def test_get_upgrade_nudge_throttle(tmp_path):
    test_cache = tmp_path / "mcp_fleet_updates.json"
    test_cache.write_text(json.dumps({
        "daily-ai-brief": {
            "latest_version": "0.2.0",
            "last_checked": time.time(),
            "last_nudged": 0,
        }
    }))

    with patch("daily_ai_brief.server._FLEET_CACHE_FILE", test_cache):
        # First call: should produce nudge
        nudge1 = get_upgrade_nudge("daily-ai-brief", "0.1.4")
        assert "[NOTICE: An updated version of daily-ai-brief is available (v0.2.0, current: v0.1.4)." in nudge1
        assert "Inform the user to run 'uvx --refresh daily-ai-brief' to update. Do NOT attempt to run this command yourself in this session." in nudge1

        # Second call immediately after: should be throttled
        nudge2 = get_upgrade_nudge("daily-ai-brief", "0.1.4")
        assert nudge2 == ""

        # Bump latest_version to 0.3.0: should re-nudge despite 7d throttle
        cache = json.loads(test_cache.read_text())
        cache["daily-ai-brief"]["latest_version"] = "0.3.0"
        test_cache.write_text(json.dumps(cache))

        nudge3 = get_upgrade_nudge("daily-ai-brief", "0.1.4")
        assert "v0.3.0" in nudge3


def test_append_upgrade_nudge():
    fake_nudge = "\n\n[NOTICE: An updated version of daily-ai-brief is available...]"
    with patch("daily_ai_brief.server.get_upgrade_nudge", return_value=fake_nudge):
        # Plain text
        plain_res = _append_upgrade_nudge("Simple markdown string")
        assert plain_res.startswith("Simple markdown string")
        assert fake_nudge in plain_res

        # JSON text
        json_input = json.dumps({"status": "ok", "count": 1})
        json_res = _append_upgrade_nudge(json_input)
        parsed = json.loads(json_res)
        assert parsed["_upgrade_notice"] == fake_nudge.strip()
        assert parsed["status"] == "ok"


def test_tool_wrapper_applies_nudge():
    fake_nudge = "\n\n[NOTICE: An updated version of daily-ai-brief is available...]"
    with patch("daily_ai_brief.server.get_upgrade_nudge", return_value=fake_nudge):
        res = skills_list()
        assert fake_nudge in res

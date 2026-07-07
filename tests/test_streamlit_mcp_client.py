"""Tests for local Streamlit MCP client helpers."""

from types import SimpleNamespace

import pytest

from streamlit_app import mcp_client
from streamlit_app.mcp_client import (
    MCPClientError,
    call_explain_tradeoffs,
    call_optimize_lineup,
    call_parse_preferences,
)


def test_call_parse_preferences_uses_mcp_tool_name(monkeypatch):
    calls = []

    def fake_run(tool_name, arguments):
        calls.append((tool_name, arguments))
        return {"parsed_preferences": {"banned_teams": ["TOR"]}}

    monkeypatch.setattr(mcp_client, "_run_mcp_tool_sync", fake_run)

    result = call_parse_preferences("avoid Toronto")

    assert calls == [("parse_preferences_tool", {"user_text": "avoid Toronto"})]
    assert result["parsed_preferences"]["banned_teams"] == ["TOR"]


def test_call_optimize_lineup_uses_mcp_tool_name_with_pool_records(monkeypatch):
    pool_records = [
        {
            "box": 1,
            "name": "Player One",
            "team": "EDM",
            "projected_points": 10,
        }
    ]
    preferences = {
        "locked_players": [],
        "banned_players": [],
        "banned_teams": [],
        "preferred_teams": [],
        "risk_mode": "balanced",
        "strategy": "balanced",
    }
    calls = []

    def fake_run(tool_name, arguments):
        calls.append((tool_name, arguments))
        return {"lineup": [pool_records[0]]}

    monkeypatch.setattr(mcp_client, "_run_mcp_tool_sync", fake_run)

    result = call_optimize_lineup(preferences, pool_records)

    assert calls == [
        (
            "optimize_lineup_tool",
            {
                "preferences": preferences,
                "pool_records": pool_records,
            },
        )
    ]
    assert result["lineup"][0]["name"] == "Player One"


def test_call_explain_tradeoffs_uses_mcp_tool_name_with_pool_records(monkeypatch):
    pool_records = [
        {
            "box": 1,
            "name": "Player One",
            "team": "EDM",
            "projected_points": 10,
        }
    ]
    preferences = {
        "locked_players": [],
        "banned_players": [],
        "banned_teams": [],
        "preferred_teams": [],
        "risk_mode": "balanced",
        "strategy": "balanced",
    }
    calls = []

    def fake_run(tool_name, arguments):
        calls.append((tool_name, arguments))
        return {"total_projected_points": 10}

    monkeypatch.setattr(mcp_client, "_run_mcp_tool_sync", fake_run)

    result = call_explain_tradeoffs(preferences, pool_records)

    assert calls == [
        (
            "explain_tradeoffs_tool",
            {
                "preferences": preferences,
                "pool_records": pool_records,
            },
        )
    ]
    assert result["total_projected_points"] == 10


def test_decode_mcp_tool_result_reads_json_text_content():
    result = SimpleNamespace(
        content=[
            SimpleNamespace(
                text='{"total_projected_points": 10, "lineup": []}',
            )
        ],
    )

    assert mcp_client._decode_mcp_tool_result(result) == {
        "total_projected_points": 10,
        "lineup": [],
    }


def test_decode_mcp_tool_result_reads_structured_content():
    result = SimpleNamespace(
        structured_content={"tradeoff_explanation": "Selected best available player."}
    )

    assert mcp_client._decode_mcp_tool_result(result) == {
        "tradeoff_explanation": "Selected best available player."
    }


def test_decode_mcp_tool_result_rejects_invalid_json():
    result = SimpleNamespace(content=[SimpleNamespace(text="not json")])

    with pytest.raises(MCPClientError, match="invalid JSON"):
        mcp_client._decode_mcp_tool_result(result)

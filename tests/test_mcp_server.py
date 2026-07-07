"""Tests for MCP server tool wrappers."""

import builtins

import pytest

from mcp_server.server import (
    create_server,
    explain_tradeoffs_tool,
    optimize_lineup_tool,
    parse_preferences_tool,
)


def test_parse_preferences_tool_returns_structured_preferences():
    result = parse_preferences_tool("I really want McDavid and avoid Toronto")
    preferences = result["parsed_preferences"]

    assert result["clarification_needed"] is False
    assert preferences["locked_players"] == ["Connor McDavid"]
    assert preferences["banned_teams"] == ["TOR"]


def test_optimize_lineup_tool_returns_lineup_result():
    result = optimize_lineup_tool(
        {
            "locked_players": ["Connor McDavid"],
            "banned_teams": [],
            "risk_mode": "balanced",
            "strategy": "balanced",
        }
    )

    assert result["lineup"][0]["name"] == "Connor McDavid"
    assert "total_projected_points" in result
    assert "total_adjusted_score" in result
    assert "tradeoff_explanation" in result


def test_explain_tradeoffs_tool_returns_summary_fields():
    result = explain_tradeoffs_tool(
        {
            "locked_players": [],
            "banned_teams": [],
            "risk_mode": "safe",
            "strategy": "chalk",
        }
    )

    assert set(result) == {
        "tradeoff_explanation",
        "total_projected_points",
        "total_adjusted_score",
    }
    assert "selected" in result["tradeoff_explanation"]


def test_create_server_reports_missing_mcp_sdk_when_not_installed(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "mcp.server.fastmcp":
            raise ModuleNotFoundError("No module named 'mcp'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match="Python MCP SDK is not installed"):
        create_server()

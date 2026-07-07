"""Basic acceptance tests for validation, parsing, and optimization."""

import pytest

from agent.preference_parser import extract_parsed_preferences, parse_preferences
from tools.optimizer import optimize_lineup
from tools.validators import validate_preferences


def test_invalid_risk_mode_raises_error():
    with pytest.raises(ValueError, match="risk_mode must be one of"):
        validate_preferences(
            risk_mode="chaotic",
            strategy="balanced",
            csv_path="data/sample_pool.csv",
            locked_players=[],
            banned_teams=[],
        )


def test_avoid_toronto_maps_to_tor():
    preferences = extract_parsed_preferences(parse_preferences("avoid Toronto"))

    assert preferences["banned_teams"] == ["TOR"]


def test_locked_mcdavid_is_selected():
    result = optimize_lineup(
        {
            "risk_mode": "balanced",
            "strategy": "balanced",
            "locked_players": ["Connor McDavid"],
            "banned_teams": [],
        }
    )

    selected_names = [player["name"] for player in result["lineup"]]

    assert "Connor McDavid" in selected_names


def test_banned_tor_players_are_excluded():
    result = optimize_lineup(
        {
            "risk_mode": "balanced",
            "strategy": "balanced",
            "locked_players": [],
            "banned_teams": ["TOR"],
        }
    )

    selected_teams = [player["team"] for player in result["lineup"]]

    assert "TOR" not in selected_teams

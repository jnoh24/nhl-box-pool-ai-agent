"""Tests for rule-based preference parsing."""

import pytest

from agent.preference_parser import parse_preferences


def test_parse_preferences_returns_defaults_for_empty_text():
    assert parse_preferences("") == {
        "locked_players": [],
        "banned_players": [],
        "banned_teams": [],
        "risk_mode": "balanced",
        "strategy": "balanced",
        "avoid_expensive": False,
        "preferred_teams": [],
    }


def test_parse_preferences_locks_mcdavid_from_natural_language():
    preferences = parse_preferences("I really want McDavid")

    assert preferences["locked_players"] == ["Connor McDavid"]


def test_parse_preferences_bans_toronto():
    preferences = parse_preferences("avoid Toronto")

    assert preferences["banned_teams"] == ["TOR"]


@pytest.mark.parametrize(
    ("prompt", "player_name"),
    [
        ("avoid Auston Matthews", "Auston Matthews"),
        ("no Connor McDavid", "Connor McDavid"),
        ("I don't want Sidney Crosby", "Sidney Crosby"),
        ("exclude Nathan MacKinnon", "Nathan MacKinnon"),
    ],
)
def test_parse_preferences_bans_player_aliases(prompt, player_name):
    preferences = parse_preferences(prompt)

    assert preferences["banned_players"] == [player_name]
    assert preferences["locked_players"] == []


@pytest.mark.parametrize(
    ("prompt", "team_code"),
    [
        ("I don't want any players from Edmonton", "EDM"),
        ("no Edmonton players", "EDM"),
        ("avoid Edmonton", "EDM"),
        ("ban Edmonton", "EDM"),
        ("exclude Edmonton", "EDM"),
        ("avoid Oilers", "EDM"),
        ("ban EDM", "EDM"),
        ("I don't want players from Toronto", "TOR"),
        ("avoid Maple Leafs", "TOR"),
        ("no Leafs players", "TOR"),
        ("exclude TOR", "TOR"),
        ("avoid Boston", "BOS"),
        ("ban Bruins", "BOS"),
        ("no BOS players", "BOS"),
    ],
)
def test_parse_preferences_bans_team_aliases(prompt, team_code):
    assert parse_preferences(prompt)["banned_teams"] == [team_code]


def test_parse_preferences_bans_edmonton_from_requested_prompt():
    preferences = parse_preferences(
        "give me the highest possible combination, but I don't want any players from Edmonton"
    )

    assert preferences["banned_teams"] == ["EDM"]


@pytest.mark.parametrize(
    ("prompt", "team_codes"),
    [
        ("as many Winnipeg Jets as possible", ["WPG"]),
        ("I want more Jets", ["WPG"]),
        ("prioritize WPG", ["WPG"]),
        ("most Winnipeg Jets and Colorado players", ["WPG", "COL"]),
        ("prioritize Colorado", ["COL"]),
        ("prefer Avalanche players", ["COL"]),
        ("prefer Avs players", ["COL"]),
        ("prioritize COL", ["COL"]),
        ("I want players from Colorado", ["COL"]),
        ("I really want players from Colorado", ["COL"]),
        ("players from Colorado", ["COL"]),
        ("I want Colorado players", ["COL"]),
        ("prefer Colorado", ["COL"]),
        ("as many Colorado players as possible", ["COL"]),
        ("I want players from Avalanche", ["COL"]),
        ("I want Avs players", ["COL"]),
        ("prefer Edmonton players", ["EDM"]),
        ("I want more Oilers", ["EDM"]),
        ("I want Edmonton players", ["EDM"]),
        ("as many EDM players as possible", ["EDM"]),
        ("I want players from Winnipeg", ["WPG"]),
        ("I really want Jets players", ["WPG"]),
        ("players from WPG", ["WPG"]),
        ("I want players from Toronto", ["TOR"]),
        ("I really want Maple Leafs players", ["TOR"]),
        ("players from Leafs", ["TOR"]),
    ],
)
def test_parse_preferences_detects_preferred_team_aliases(prompt, team_codes):
    assert parse_preferences(prompt)["preferred_teams"] == team_codes


def test_parse_preferences_team_wants_do_not_lock_players():
    preferences = parse_preferences("I really want players from Colorado")

    assert preferences["preferred_teams"] == ["COL"]
    assert preferences["locked_players"] == []


def test_parse_preferences_does_not_confuse_banned_and_preferred_teams():
    preferences = parse_preferences("avoid Edmonton but prioritize Colorado")

    assert preferences["banned_teams"] == ["EDM"]
    assert preferences["preferred_teams"] == ["COL"]


def test_parse_preferences_detects_safe_lineup():
    preferences = parse_preferences("Give me a safe lineup")

    assert preferences["risk_mode"] == "safe"
    assert parse_preferences("I want low risk picks")["risk_mode"] == "safe"
    assert parse_preferences("Give me consistent players")["risk_mode"] == "safe"


def test_parse_preferences_detects_risky_lineup():
    preferences = parse_preferences("Build a risky lineup")

    assert preferences["risk_mode"] == "risky"
    assert parse_preferences("I want high upside picks")["risk_mode"] == "risky"
    assert parse_preferences("Give me a boom or bust lineup")["risk_mode"] == "risky"


def test_parse_preferences_detects_contrarian_strategy():
    assert parse_preferences("I want a contrarian build")["strategy"] == "contrarian"
    assert parse_preferences("Find me a sleeper pick")["strategy"] == "contrarian"
    assert parse_preferences("Make it unique")["strategy"] == "contrarian"
    assert parse_preferences("Give me something different")["strategy"] == "contrarian"


def test_parse_preferences_detects_chalk_strategy():
    assert parse_preferences("Use popular picks")["strategy"] == "chalk"
    assert parse_preferences("Give me chalk")["strategy"] == "chalk"
    assert parse_preferences("Use obvious picks")["strategy"] == "chalk"


def test_parse_preferences_detects_avoid_expensive():
    assert parse_preferences("avoid expensive players")["avoid_expensive"] is True
    assert parse_preferences("Give me cheap options")["avoid_expensive"] is True
    assert parse_preferences("Build around low salary picks")["avoid_expensive"] is True


def test_parse_preferences_can_combine_rules():
    preferences = parse_preferences("Safe lineup, I want Makar and avoid Boston")

    assert preferences["locked_players"] == ["Cale Makar"]
    assert preferences["banned_teams"] == ["BOS"]
    assert preferences["risk_mode"] == "safe"


def test_parse_preferences_rejects_non_string_input():
    with pytest.raises(ValueError, match="user_text must be a string"):
        parse_preferences(None)

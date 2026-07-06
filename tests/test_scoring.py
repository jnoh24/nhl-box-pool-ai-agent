"""Tests for score calculations."""

import pytest

from tools.scoring import score_player


def test_score_player_uses_projected_points_as_base_score():
    score = score_player(
        {"name": "Player One", "projected_points": 100},
        {"risk_mode": "risky", "strategy": "balanced", "locked_players": []},
    )

    assert score == 100


def test_score_player_applies_risk_penalty():
    safe_score = score_player(
        {"name": "Player One", "projected_points": 100, "risk": "high"},
        {"risk_mode": "safe", "strategy": "balanced", "locked_players": []},
    )
    balanced_score = score_player(
        {"name": "Player One", "projected_points": 100, "risk": "high"},
        {"risk_mode": "balanced", "strategy": "balanced", "locked_players": []},
    )
    risky_score = score_player(
        {"name": "Player One", "projected_points": 100, "risk": "high"},
        {"risk_mode": "risky", "strategy": "balanced", "locked_players": []},
    )

    assert safe_score == 91
    assert balanced_score == 95
    assert risky_score == 98.5


def test_score_player_applies_injury_penalty():
    score = score_player(
        {"name": "Player One", "projected_points": 100, "injury_status": "questionable"},
        {"risk_mode": "risky", "strategy": "balanced", "locked_players": []},
    )

    assert score == 92


def test_score_player_chalk_rewards_popularity():
    score = score_player(
        {"name": "Player One", "projected_points": 100, "popularity": 0.8},
        {"risk_mode": "risky", "strategy": "chalk", "locked_players": []},
    )

    assert score == 108


def test_score_player_contrarian_rewards_lower_popularity():
    score = score_player(
        {"name": "Player One", "projected_points": 100, "popularity": 0.2},
        {"risk_mode": "risky", "strategy": "contrarian", "locked_players": []},
    )

    assert score == 108


def test_score_player_popularity_changes_chalk_and_contrarian_rankings():
    popular_player = {"name": "Popular Player", "projected_points": 100, "popularity": 0.9}
    unpopular_player = {"name": "Unpopular Player", "projected_points": 100, "popularity": 0.1}

    chalk_preferences = {"risk_mode": "risky", "strategy": "chalk", "locked_players": []}
    contrarian_preferences = {
        "risk_mode": "risky",
        "strategy": "contrarian",
        "locked_players": [],
    }

    assert score_player(popular_player, chalk_preferences) > score_player(
        unpopular_player,
        chalk_preferences,
    )
    assert score_player(unpopular_player, contrarian_preferences) > score_player(
        popular_player,
        contrarian_preferences,
    )


def test_score_player_balanced_strategy_ignores_popularity():
    popular_score = score_player(
        {"name": "Player One", "projected_points": 100, "popularity": 0.9},
        {"risk_mode": "risky", "strategy": "balanced", "locked_players": []},
    )
    unpopular_score = score_player(
        {"name": "Player Two", "projected_points": 100, "popularity": 0.1},
        {"risk_mode": "risky", "strategy": "balanced", "locked_players": []},
    )

    assert popular_score == unpopular_score == 100


def test_score_player_adds_preferred_team_bonus():
    score = score_player(
        {"name": "Player One", "team": "WPG", "projected_points": 100},
        {
            "risk_mode": "risky",
            "strategy": "balanced",
            "locked_players": [],
            "preferred_teams": ["WPG"],
        },
    )

    assert score == 103


def test_score_player_adds_locked_player_bonus():
    score = score_player(
        {"name": "Player One", "projected_points": 100},
        {"risk_mode": "risky", "strategy": "balanced", "locked_players": ["Player One"]},
    )

    assert score == 110


def test_score_player_requires_projected_points():
    with pytest.raises(ValueError, match="player_row must include projected_points"):
        score_player(
            {"name": "Player One"},
            {"risk_mode": "risky", "strategy": "balanced", "locked_players": []},
        )


def test_score_player_rejects_invalid_strategy():
    with pytest.raises(ValueError, match="strategy must be one of"):
        score_player(
            {"name": "Player One", "projected_points": 100},
            {"risk_mode": "risky", "strategy": "stars", "locked_players": []},
        )

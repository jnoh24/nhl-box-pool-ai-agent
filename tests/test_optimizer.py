"""Tests for lineup optimization."""

from collections import Counter

import pytest

from tools.optimizer import optimize_lineup


def test_optimize_lineup_selects_one_player_from_each_box():
    result = optimize_lineup(
        {
            "risk_mode": "balanced",
            "strategy": "balanced",
            "locked_players": [],
            "banned_teams": [],
        }
    )

    boxes = [player["box"] for player in result["lineup"]]

    assert boxes == [str(box) for box in range(1, 16)]
    assert Counter(boxes) == {str(box): 1 for box in range(1, 16)}
    assert len(result["lineup"]) == 15
    assert result["total_projected_points"] == sum(
        player["projected_points"] for player in result["lineup"]
    )
    assert result["total_adjusted_score"] == sum(
        player["adjusted_score"] for player in result["lineup"]
    )
    assert "highest adjusted score" in result["tradeoff_explanation"]


def test_optimize_lineup_returns_lineup_sorted_by_box():
    result = optimize_lineup(
        {
            "risk_mode": "balanced",
            "strategy": "balanced",
            "locked_players": [],
            "banned_teams": [],
        }
    )

    boxes = [int(player["box"]) for player in result["lineup"]]

    assert boxes == sorted(boxes)


def test_optimize_lineup_selects_locked_player_automatically():
    result = optimize_lineup(
        {
            "risk_mode": "balanced",
            "strategy": "balanced",
            "locked_players": ["Nathan MacKinnon"],
            "banned_teams": [],
        }
    )

    locked_player = next(player for player in result["lineup"] if player["name"] == "Nathan MacKinnon")

    assert locked_player["box"] == "1"
    assert "selected locked player Nathan MacKinnon" in result["tradeoff_explanation"]


def test_optimize_lineup_respects_banned_teams():
    result = optimize_lineup(
        {
            "risk_mode": "balanced",
            "strategy": "balanced",
            "locked_players": [],
            "banned_teams": ["EDM"],
        }
    )

    selected_teams = [player["team"] for player in result["lineup"]]

    assert "EDM" not in selected_teams
    assert len(result["lineup"]) == 15


def test_optimize_lineup_respects_banned_players():
    result = optimize_lineup(
        {
            "risk_mode": "balanced",
            "strategy": "balanced",
            "locked_players": [],
            "banned_players": ["Connor McDavid"],
            "banned_teams": [],
        }
    )

    selected_names = [player["name"] for player in result["lineup"]]

    assert "Connor McDavid" not in selected_names
    assert len(result["lineup"]) == 15


def test_optimize_lineup_applies_preferred_team_bonus_in_close_boxes():
    result = optimize_lineup(
        {
            "risk_mode": "balanced",
            "strategy": "balanced",
            "locked_players": [],
            "banned_teams": [],
            "preferred_teams": ["WPG"],
        }
    )

    box_ten_player = next(player for player in result["lineup"] if player["box"] == "10")

    assert box_ten_player["name"] == "Josh Morrissey"
    assert box_ten_player["team"] == "WPG"
    assert "Preferred teams considered: WPG" in result["tradeoff_explanation"]
    assert "Preferred team bonus applied for WPG" in result["tradeoff_explanation"]


def test_optimize_lineup_rejects_locked_player_on_banned_team():
    with pytest.raises(ValueError, match="Locked player Connor McDavid is on banned team EDM"):
        optimize_lineup(
            {
                "risk_mode": "balanced",
                "strategy": "balanced",
                "locked_players": ["Connor McDavid"],
                "banned_teams": ["EDM"],
            }
        )


def test_optimize_lineup_rejects_player_that_is_locked_and_banned():
    with pytest.raises(
        ValueError,
        match="Players cannot be both locked and banned: Connor McDavid",
    ):
        optimize_lineup(
            {
                "risk_mode": "balanced",
                "strategy": "balanced",
                "locked_players": ["Connor McDavid"],
                "banned_players": ["Connor McDavid"],
                "banned_teams": [],
            }
        )


def test_optimize_lineup_rejects_invalid_risk_mode():
    with pytest.raises(ValueError, match="risk_mode must be one of"):
        optimize_lineup(
            {
                "risk_mode": "wild",
                "strategy": "balanced",
                "locked_players": [],
                "banned_teams": [],
            }
        )

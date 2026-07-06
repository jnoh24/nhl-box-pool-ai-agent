"""Tests for lineup optimization."""

from collections import Counter

import pandas as pd
import pytest

from tools.optimizer import optimize_lineup


def _uploaded_pool_df(include_popularity: bool = True, include_risk: bool = True):
    rows = [
        {
            "box": 1,
            "name": "Safe Player",
            "team": "DAL",
            "projected_points": 10,
            "popularity": 1.0,
            "risk": "low",
        },
        {
            "box": 1,
            "name": "Contrarian Player",
            "team": "MIN",
            "projected_points": 9,
            "popularity": 0.0,
            "risk": "low",
        },
        {
            "box": 2,
            "name": "Preferred Player",
            "team": "WPG",
            "projected_points": 10,
            "popularity": 0.5,
            "risk": "low",
        },
        {
            "box": 2,
            "name": "Slightly Better Player",
            "team": "COL",
            "projected_points": 12,
            "popularity": 0.5,
            "risk": "low",
        },
    ]
    if not include_popularity:
        for row in rows:
            row.pop("popularity")
    if not include_risk:
        for row in rows:
            row.pop("risk")
    return pd.DataFrame(rows)


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


def test_optimize_lineup_uses_provided_pool_dataframe():
    result = optimize_lineup(
        {
            "risk_mode": "balanced",
            "strategy": "balanced",
            "locked_players": [],
            "banned_players": [],
            "banned_teams": [],
            "preferred_teams": [],
        },
        pool_df=_uploaded_pool_df(),
    )

    assert [player["box"] for player in result["lineup"]] == ["1", "2"]
    assert [player["name"] for player in result["lineup"]] == [
        "Safe Player",
        "Slightly Better Player",
    ]


def test_optimize_lineup_requires_projected_points_for_dataframe():
    pool_df = pd.DataFrame(
        [
            {
                "box": 1,
                "name": "Safe Player",
                "team": "DAL",
            }
        ]
    )

    with pytest.raises(ValueError, match="Optimization requires projected_points"):
        optimize_lineup(
            {
                "risk_mode": "balanced",
                "strategy": "balanced",
                "locked_players": [],
                "banned_players": [],
                "banned_teams": [],
            },
            pool_df=pool_df,
        )


def test_optimize_lineup_treats_missing_popularity_as_balanced_strategy():
    result = optimize_lineup(
        {
            "risk_mode": "balanced",
            "strategy": "contrarian",
            "locked_players": [],
            "banned_players": [],
            "banned_teams": [],
        },
        pool_df=_uploaded_pool_df(include_popularity=False),
    )

    box_one_player = next(player for player in result["lineup"] if player["box"] == "1")

    assert box_one_player["name"] == "Safe Player"


def test_optimize_lineup_treats_missing_risk_as_balanced_risk_mode():
    result = optimize_lineup(
        {
            "risk_mode": "safe",
            "strategy": "balanced",
            "locked_players": [],
            "banned_players": [],
            "banned_teams": [],
        },
        pool_df=_uploaded_pool_df(include_risk=False),
    )

    assert len(result["lineup"]) == 2


def test_optimize_lineup_respects_constraints_with_dataframe():
    result = optimize_lineup(
        {
            "risk_mode": "balanced",
            "strategy": "balanced",
            "locked_players": ["Contrarian Player"],
            "banned_players": ["Slightly Better Player"],
            "banned_teams": [],
            "preferred_teams": ["WPG"],
        },
        pool_df=_uploaded_pool_df(),
    )

    selected_names = [player["name"] for player in result["lineup"]]

    assert "Contrarian Player" in selected_names
    assert "Slightly Better Player" not in selected_names
    assert "Preferred Player" in selected_names

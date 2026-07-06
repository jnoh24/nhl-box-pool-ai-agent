"""Tests for uploaded pool data intake."""

from io import StringIO

import pandas as pd
import pytest

from tools.data_intake import (
    check_optimization_readiness,
    load_uploaded_pool,
    normalize_pool_dataframe,
    validate_minimum_schema,
)


def test_load_uploaded_pool_normalizes_safe_defaults():
    csv_file = StringIO(
        "box,name,team,projected_points,popularity,risk\n"
        "1,Connor McDavid,EDM,120,0.9,low\n"
        "1,Nathan MacKinnon,COL,118,0.8,medium\n"
    )

    df = load_uploaded_pool(csv_file)

    assert list(df["player_id"]) == [1, 2]
    assert list(df["position"]) == ["UNKNOWN", "UNKNOWN"]
    assert list(df["injury_status"]) == ["unknown", "unknown"]
    assert list(df["salary"]) == [0, 0]


def test_normalize_pool_dataframe_does_not_invent_scoring_inputs():
    df = pd.DataFrame(
        [
            {
                "box": 1,
                "name": "Connor McDavid",
                "team": "EDM",
            }
        ]
    )

    normalized = normalize_pool_dataframe(df)

    assert "projected_points" not in normalized.columns
    assert "popularity" not in normalized.columns
    assert "risk" not in normalized.columns


def test_validate_minimum_schema_rejects_missing_required_columns():
    df = pd.DataFrame([{"box": 1, "name": "Connor McDavid"}])

    with pytest.raises(ValueError, match="missing required columns: team"):
        validate_minimum_schema(df)


def test_check_optimization_readiness_requires_projected_points():
    df = normalize_pool_dataframe(
        pd.DataFrame(
            [
                {
                    "box": 1,
                    "name": "Connor McDavid",
                    "team": "EDM",
                    "popularity": 0.9,
                    "risk": "low",
                }
            ]
        )
    )

    report = check_optimization_readiness(df)

    assert report["optimization_ready"] is False
    assert "projected_points" in report["missing_optional_columns"]
    assert "Missing projected_points; optimization cannot run." in report["messages"]


def test_check_optimization_readiness_allows_missing_popularity_but_disables_strategy():
    df = normalize_pool_dataframe(
        pd.DataFrame(
            [
                {
                    "box": 1,
                    "name": "Connor McDavid",
                    "team": "EDM",
                    "projected_points": 120,
                    "risk": "low",
                }
            ]
        )
    )

    report = check_optimization_readiness(df)

    assert report["optimization_ready"] is True
    assert report["can_use_chalk_contrarian"] is False
    assert "chalk_and_contrarian_strategy" in report["disabled_features"]


def test_check_optimization_readiness_allows_missing_risk_but_disables_risk_modes():
    df = normalize_pool_dataframe(
        pd.DataFrame(
            [
                {
                    "box": 1,
                    "name": "Connor McDavid",
                    "team": "EDM",
                    "projected_points": 120,
                    "popularity": 0.9,
                }
            ]
        )
    )

    report = check_optimization_readiness(df)

    assert report["optimization_ready"] is True
    assert report["can_use_risk_modes"] is False
    assert "risk_based_modes" in report["disabled_features"]


def test_check_optimization_readiness_reports_ready_dataset():
    df = normalize_pool_dataframe(
        pd.DataFrame(
            [
                {
                    "box": 1,
                    "name": "Connor McDavid",
                    "team": "EDM",
                    "projected_points": 120,
                    "popularity": 0.9,
                    "risk": "low",
                }
            ]
        )
    )

    report = check_optimization_readiness(df)

    assert report["optimization_ready"] is True
    assert report["disabled_features"] == []
    assert report["messages"] == ["Dataset is ready for optimization."]

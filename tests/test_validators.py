"""Tests for input validators."""

from pathlib import Path

import pytest

from tools.validators import validate_csv_schema, validate_preferences


CSV_HEADER = (
    "box,player_id,name,team,position,projected_points,risk,"
    "injury_status,popularity,salary"
)


def _valid_csv_text() -> str:
    rows = [CSV_HEADER]
    for box in range(1, 16):
        rows.append(
            f"{box},{box},Player {box},EDM,C,70.5,medium,healthy,0.50,6000"
        )
    return "\n".join(rows) + "\n"


def _write_csv(tmp_path: Path, content: str) -> Path:
    csv_path = tmp_path / "sample_pool.csv"
    csv_path.write_text(content, encoding="utf-8")
    return csv_path


def test_validate_preferences_accepts_valid_input():
    result = validate_preferences(
        risk_mode="balanced",
        strategy="contrarian",
        csv_path="data/sample_pool.csv",
        locked_players=["Connor McDavid"],
        banned_teams=["BOS"],
    )

    assert result == {
        "risk_mode": "balanced",
        "strategy": "contrarian",
        "csv_path": Path("data/sample_pool.csv"),
        "locked_players": ["Connor McDavid"],
        "banned_players": [],
        "banned_teams": ["BOS"],
        "preferred_teams": [],
    }


def test_validate_preferences_rejects_invalid_risk_mode():
    with pytest.raises(ValueError, match="risk_mode must be one of"):
        validate_preferences("aggressive", "balanced", "data/sample_pool.csv", [], [])


def test_validate_preferences_rejects_invalid_strategy():
    with pytest.raises(ValueError, match="strategy must be one of"):
        validate_preferences("safe", "popular", "data/sample_pool.csv", [], [])


def test_validate_preferences_rejects_unapproved_csv_path():
    with pytest.raises(ValueError, match="csv_path must be exactly data/sample_pool.csv"):
        validate_preferences("safe", "chalk", "data/other.csv", [], [])


def test_validate_preferences_rejects_non_list_locked_players():
    with pytest.raises(ValueError, match="locked_players must be a list of strings"):
        validate_preferences("safe", "chalk", "data/sample_pool.csv", "Connor McDavid", [])


def test_validate_preferences_rejects_non_string_locked_player():
    with pytest.raises(ValueError, match="locked_players must contain only strings"):
        validate_preferences("safe", "chalk", "data/sample_pool.csv", [99], [])


def test_validate_preferences_rejects_non_list_banned_players():
    with pytest.raises(ValueError, match="banned_players must be a list of strings"):
        validate_preferences(
            "safe",
            "chalk",
            "data/sample_pool.csv",
            [],
            [],
            banned_players="Auston Matthews",
        )


def test_validate_preferences_rejects_non_string_banned_player():
    with pytest.raises(ValueError, match="banned_players must contain only strings"):
        validate_preferences(
            "safe",
            "chalk",
            "data/sample_pool.csv",
            [],
            [],
            banned_players=[99],
        )


def test_validate_preferences_rejects_non_list_banned_teams():
    with pytest.raises(ValueError, match="banned_teams must be a list of strings"):
        validate_preferences("safe", "chalk", "data/sample_pool.csv", [], "BOS")


def test_validate_preferences_rejects_non_string_banned_team():
    with pytest.raises(ValueError, match="banned_teams must contain only strings"):
        validate_preferences("safe", "chalk", "data/sample_pool.csv", [], [123])


def test_validate_preferences_rejects_non_list_preferred_teams():
    with pytest.raises(ValueError, match="preferred_teams must be a list of strings"):
        validate_preferences(
            "safe",
            "chalk",
            "data/sample_pool.csv",
            [],
            [],
            preferred_teams="WPG",
        )


def test_validate_csv_schema_accepts_valid_sample_file():
    assert validate_csv_schema("data/sample_pool.csv") == Path("data/sample_pool.csv")


def test_validate_csv_schema_rejects_missing_required_column(tmp_path, monkeypatch):
    csv_path = _write_csv(tmp_path, _valid_csv_text().replace(",salary", ""))
    monkeypatch.setattr("tools.validators.ALLOWED_CSV_PATH", csv_path)

    with pytest.raises(ValueError, match="missing required columns: salary"):
        validate_csv_schema(csv_path)


def test_validate_csv_schema_rejects_missing_box_column(tmp_path, monkeypatch):
    csv_text = _valid_csv_text().replace("box,", "", 1)
    csv_path = _write_csv(tmp_path, csv_text)
    monkeypatch.setattr("tools.validators.ALLOWED_CSV_PATH", csv_path)

    with pytest.raises(ValueError, match="missing required columns: box"):
        validate_csv_schema(csv_path)


def test_validate_csv_schema_rejects_non_integer_box(tmp_path, monkeypatch):
    csv_path = _write_csv(tmp_path, _valid_csv_text().replace("1,1,Player 1", "A,1,Player 1"))
    monkeypatch.setattr("tools.validators.ALLOWED_CSV_PATH", csv_path)

    with pytest.raises(ValueError, match="Row 2 box must be an integer"):
        validate_csv_schema(csv_path)


def test_validate_csv_schema_rejects_popularity_outside_zero_to_one(tmp_path, monkeypatch):
    csv_path = _write_csv(tmp_path, _valid_csv_text().replace("0.50", "1.50", 1))
    monkeypatch.setattr("tools.validators.ALLOWED_CSV_PATH", csv_path)

    with pytest.raises(ValueError, match="Row 2 popularity must be between 0 and 1"):
        validate_csv_schema(csv_path)


def test_validate_csv_schema_rejects_unknown_risk(tmp_path, monkeypatch):
    csv_path = _write_csv(tmp_path, _valid_csv_text().replace("medium", "volatile", 1))
    monkeypatch.setattr("tools.validators.ALLOWED_CSV_PATH", csv_path)

    with pytest.raises(ValueError, match="Row 2 risk must be one of"):
        validate_csv_schema(csv_path)


def test_validate_csv_schema_rejects_unknown_injury_status(tmp_path, monkeypatch):
    csv_path = _write_csv(tmp_path, _valid_csv_text().replace("healthy", "day-to-day", 1))
    monkeypatch.setattr("tools.validators.ALLOWED_CSV_PATH", csv_path)

    with pytest.raises(ValueError, match="Row 2 injury_status must be one of"):
        validate_csv_schema(csv_path)


def test_validate_csv_schema_rejects_empty_box(tmp_path, monkeypatch):
    csv_text = _valid_csv_text().replace("7,7,Player 7", "8,7,Player 7")
    csv_path = _write_csv(tmp_path, csv_text)
    monkeypatch.setattr("tools.validators.ALLOWED_CSV_PATH", csv_path)

    with pytest.raises(ValueError, match="empty boxes: 7"):
        validate_csv_schema(csv_path)

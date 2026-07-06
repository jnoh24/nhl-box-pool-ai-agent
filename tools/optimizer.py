"""Lineup optimization helpers."""

import csv
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from tools.scoring import score_player
from tools.validators import validate_preferences


DEFAULT_CSV_PATH = Path("data/sample_pool.csv")
REQUIRED_COLUMNS = {
    "box",
    "player_id",
    "name",
    "team",
    "position",
    "projected_points",
    "risk",
    "injury_status",
    "popularity",
    "salary",
}
MINIMUM_POOL_COLUMNS = {"box", "name", "team", "projected_points"}
EXPECTED_BOXES = {str(box) for box in range(1, 16)}


def _load_players(csv_path: Path) -> list[dict[str, object]]:
    """Load player rows from the approved CSV file."""
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError("CSV file must include a header row.")

        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"CSV file is missing required columns: {missing}.")

        return [
            _normalise_player_row(row, row_number)
            for row_number, row in enumerate(reader, start=2)
        ]


def _load_players_from_dataframe(pool_df: pd.DataFrame) -> list[dict[str, object]]:
    """Load player rows from an uploaded dataframe."""
    normalized = pool_df.copy()
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]

    missing_columns = MINIMUM_POOL_COLUMNS - set(normalized.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        if "projected_points" in missing_columns:
            raise ValueError("Optimization requires projected_points in the player pool.")
        raise ValueError(f"Player pool is missing required columns: {missing}.")

    if "player_id" not in normalized.columns:
        normalized["player_id"] = range(1, len(normalized) + 1)
    if "position" not in normalized.columns:
        normalized["position"] = "UNKNOWN"
    if "injury_status" not in normalized.columns:
        normalized["injury_status"] = "unknown"
    if "salary" not in normalized.columns:
        normalized["salary"] = 0

    return [
        _normalise_dataframe_row(row, row_number)
        for row_number, row in enumerate(normalized.to_dict("records"), start=2)
    ]


def _normalise_dataframe_row(row: dict[str, object], row_number: int) -> dict[str, object]:
    """Convert dataframe rows into the types expected by optimizer output."""
    player = dict(row)
    for field_name in ("box", "player_id", "name", "team", "position"):
        if _is_missing(player.get(field_name)):
            if field_name == "position":
                player[field_name] = "UNKNOWN"
            else:
                raise ValueError(f"Row {row_number} must include a non-empty {field_name}.")

    player["box"] = str(player["box"]).strip()
    player["name"] = str(player["name"]).strip()
    player["team"] = str(player["team"]).strip()
    player["position"] = str(player.get("position", "UNKNOWN")).strip() or "UNKNOWN"
    player["injury_status"] = (
        str(player.get("injury_status", "unknown")).strip() or "unknown"
    )
    player["projected_points"] = _numeric_value(
        player["projected_points"],
        "projected_points",
    )
    player["popularity"] = _optional_numeric_value(player.get("popularity"), 0.5)
    player["salary"] = _optional_numeric_value(player.get("salary"), 0)
    if _is_missing(player.get("risk")):
        player["risk"] = "low"
    else:
        player["risk"] = str(player["risk"]).strip()
    return player


def _normalise_player_row(row: dict[str, str], row_number: int) -> dict[str, object]:
    """Convert CSV text values into the types expected by optimizer output."""
    player = {key: row[key].strip() for key in REQUIRED_COLUMNS}
    for field_name in ("box", "player_id", "name", "team", "position"):
        if not player[field_name]:
            raise ValueError(f"Row {row_number} must include a non-empty {field_name}.")

    player["projected_points"] = _numeric_value(player["projected_points"], "projected_points")
    player["popularity"] = _numeric_value(player["popularity"], "popularity")
    player["salary"] = _numeric_value(player["salary"], "salary")
    return player


def _numeric_value(value: object, field_name: str) -> float:
    """Convert a numeric CSV field to float with an optimizer-specific message."""
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Each player must include numeric {field_name}.") from exc


def _optional_numeric_value(value: object, default: float) -> float:
    """Convert an optional numeric field, falling back only when it is absent."""
    if _is_missing(value):
        return default
    return _numeric_value(value, "optional numeric field")


def _is_missing(value: object) -> bool:
    """Return whether a dataframe value is blank or missing."""
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def _projected_points(player: Mapping[str, object]) -> float:
    """Read projected points from a player row."""
    try:
        return float(player["projected_points"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Each player must include numeric projected_points.") from exc


def _group_by_box(players: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    """Group player rows by box."""
    boxes: dict[str, list[dict[str, object]]] = defaultdict(list)
    for player in players:
        box = str(player["box"]).strip()
        if not box:
            raise ValueError("Each player must include a non-empty box.")
        boxes[box].append(player)
    return dict(boxes)


def _validate_boxes(boxes: Mapping[str, list[dict[str, object]]]) -> None:
    """Ensure the pool has the expected 15 NHL box-pool boxes."""
    actual_boxes = set(boxes)
    missing_boxes = EXPECTED_BOXES - actual_boxes
    extra_boxes = actual_boxes - EXPECTED_BOXES
    if missing_boxes or extra_boxes:
        details = []
        if missing_boxes:
            details.append(
                f"missing boxes: {', '.join(sorted(missing_boxes, key=_sort_box_key))}"
            )
        if extra_boxes:
            details.append(
                f"unexpected boxes: {', '.join(sorted(extra_boxes, key=_sort_box_key))}"
            )
        raise ValueError(f"CSV must include boxes 1 through 15 ({'; '.join(details)}).")

    empty_boxes = [box for box, players in boxes.items() if not players]
    if empty_boxes:
        boxes_text = ", ".join(sorted(empty_boxes, key=_sort_box_key))
        raise ValueError(f"CSV has empty boxes: {boxes_text}.")


def _sort_box_key(box: str) -> tuple[int, object]:
    """Sort numeric boxes naturally and text boxes alphabetically."""
    if box.isdigit():
        return (0, int(box))
    return (1, box)


def _select_player_for_box(
    box: str,
    players: list[dict[str, object]],
    preferences: Mapping[str, object],
) -> tuple[dict[str, object], str]:
    """Select the best player for one box."""
    locked_players = set(preferences["locked_players"])
    banned_teams = set(preferences["banned_teams"])
    banned_players = set(preferences["banned_players"])

    locked_in_box = [player for player in players if player["name"] in locked_players]
    if len(locked_in_box) > 1:
        names = ", ".join(player["name"] for player in locked_in_box)
        raise ValueError(f"Box {box} has multiple locked players: {names}.")

    if locked_in_box:
        selected = locked_in_box[0]
        if selected["team"] in banned_teams:
            raise ValueError(
                f"Locked player {selected['name']} is on banned team {selected['team']}."
            )
        reason = f"Box {box}: selected locked player {selected['name']}."
        return _with_adjusted_score(selected, preferences), reason

    # Banned teams and players are removed before comparing adjusted scores.
    eligible_players = [
        player
        for player in players
        if player["team"] not in banned_teams and player["name"] not in banned_players
    ]
    if not eligible_players:
        raise ValueError(
            f"Box {box} has no eligible players after applying banned teams and players."
        )

    scored_players = [_with_adjusted_score(player, preferences) for player in eligible_players]
    selected = max(scored_players, key=lambda player: player["adjusted_score"])
    preference_note = ""
    if selected["team"] in preferences.get("preferred_teams", []):
        preference_note = f" Preferred team bonus applied for {selected['team']}."
    reason = (
        f"Box {box}: selected {selected['name']} with the highest adjusted score "
        f"({selected['adjusted_score']}).{preference_note}"
    )
    return selected, reason


def _with_adjusted_score(
    player: Mapping[str, object],
    preferences: Mapping[str, object],
) -> dict[str, object]:
    """Attach adjusted score and numeric projected points to a player row."""
    selected = dict(player)
    selected["projected_points"] = _projected_points(player)
    selected["popularity"] = float(selected["popularity"])
    selected["salary"] = float(selected["salary"])
    selected["adjusted_score"] = score_player(_player_for_scoring(selected), preferences)
    return selected


def _player_for_scoring(player: Mapping[str, object]) -> dict[str, object]:
    """Return a scoring copy with popularity normalized to the scorer's 0-1 scale."""
    scored_player = dict(player)
    popularity = float(scored_player["popularity"])
    if popularity > 1:
        popularity /= 100
    scored_player["popularity"] = popularity
    return scored_player


def optimize_lineup(
    preferences: Mapping[str, object],
    csv_path: str | Path = DEFAULT_CSV_PATH,
    pool_df: pd.DataFrame | None = None,
) -> dict[str, object]:
    """Build one lineup by selecting exactly one player from each box.

    Locked players win automatically within their box. Otherwise, each box uses
    the highest adjusted score after banned teams, risk mode, and strategy are applied.
    """
    risk_mode = str(preferences.get("risk_mode", "balanced"))
    strategy = str(preferences.get("strategy", "balanced"))
    if pool_df is not None:
        columns = {str(column).strip().lower() for column in pool_df.columns}
        if "projected_points" not in columns:
            raise ValueError("Optimization requires projected_points in the player pool.")
        if "popularity" not in columns:
            strategy = "balanced"
        if "risk" not in columns:
            risk_mode = "balanced"

    validated_preferences = validate_preferences(
        risk_mode=risk_mode,
        strategy=strategy,
        csv_path=csv_path,
        locked_players=preferences.get("locked_players", []),
        banned_teams=preferences.get("banned_teams", []),
        banned_players=preferences.get("banned_players", []),
        preferred_teams=preferences.get("preferred_teams", []),
        validate_csv=pool_df is None,
    )
    locked_and_banned = set(validated_preferences["locked_players"]) & set(
        validated_preferences["banned_players"]
    )
    if locked_and_banned:
        names = ", ".join(sorted(locked_and_banned))
        raise ValueError(f"Players cannot be both locked and banned: {names}.")

    players = (
        _load_players_from_dataframe(pool_df)
        if pool_df is not None
        else _load_players(validated_preferences["csv_path"])
    )
    boxes = _group_by_box(players)
    if pool_df is None:
        _validate_boxes(boxes)

    lineup = []
    explanations = []
    preferred_teams = validated_preferences.get("preferred_teams", [])
    if preferred_teams:
        explanations.append(f"Preferred teams considered: {', '.join(preferred_teams)}.")
    for box, box_players in sorted(boxes.items(), key=lambda item: _sort_box_key(item[0])):
        selected, reason = _select_player_for_box(box, box_players, validated_preferences)
        lineup.append(selected)
        explanations.append(reason)

    total_projected_points = round(sum(player["projected_points"] for player in lineup), 2)
    total_adjusted_score = round(sum(player["adjusted_score"] for player in lineup), 2)

    return {
        "lineup": lineup,
        "total_projected_points": total_projected_points,
        "total_adjusted_score": total_adjusted_score,
        "tradeoff_explanation": " ".join(explanations),
    }

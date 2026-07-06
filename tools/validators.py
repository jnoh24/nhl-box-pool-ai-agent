"""Input validation helpers."""

import csv
from collections import defaultdict
from pathlib import Path


ALLOWED_RISK_MODES = {"safe", "balanced", "risky"}
ALLOWED_STRATEGIES = {"chalk", "balanced", "contrarian"}
ALLOWED_CSV_PATH = Path("data/sample_pool.csv")
REQUIRED_CSV_COLUMNS = {
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
ALLOWED_PLAYER_RISKS = {"low", "medium", "high"}
ALLOWED_INJURY_STATUSES = {"healthy", "questionable", "out"}
EXPECTED_BOXES = set(range(1, 16))


def validate_risk_mode(risk_mode: str) -> str:
    """Validate the requested risk mode."""
    if risk_mode not in ALLOWED_RISK_MODES:
        allowed = ", ".join(sorted(ALLOWED_RISK_MODES))
        raise ValueError(f"risk_mode must be one of: {allowed}.")
    return risk_mode


def validate_strategy(strategy: str) -> str:
    """Validate the requested strategy."""
    if strategy not in ALLOWED_STRATEGIES:
        allowed = ", ".join(sorted(ALLOWED_STRATEGIES))
        raise ValueError(f"strategy must be one of: {allowed}.")
    return strategy


def validate_csv_path(csv_path: str | Path) -> Path:
    """Validate that the CSV path points to the approved sample data file."""
    path = Path(csv_path)
    if path != ALLOWED_CSV_PATH:
        raise ValueError("csv_path must be exactly data/sample_pool.csv.")
    return path


def validate_csv_schema(csv_path: str | Path) -> Path:
    """Validate the approved CSV file's schema and row-level values."""
    path = validate_csv_path(csv_path)
    boxes: dict[int, int] = defaultdict(int)

    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError("CSV file must include a header row.")

        missing_columns = REQUIRED_CSV_COLUMNS - set(reader.fieldnames)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"CSV file is missing required columns: {missing}.")

        for row_number, row in enumerate(reader, start=2):
            box = _validate_int(row.get("box"), "box", row_number)
            boxes[box] += 1
            _validate_numeric(row.get("projected_points"), "projected_points", row_number)
            _validate_numeric(row.get("salary"), "salary", row_number)
            popularity = _validate_numeric(row.get("popularity"), "popularity", row_number)
            if not 0 <= popularity <= 1:
                raise ValueError(f"Row {row_number} popularity must be between 0 and 1.")
            _validate_choice(row.get("risk"), "risk", ALLOWED_PLAYER_RISKS, row_number)
            _validate_choice(
                row.get("injury_status"),
                "injury_status",
                ALLOWED_INJURY_STATUSES,
                row_number,
            )

    if not boxes:
        raise ValueError("CSV file must include at least one player.")

    missing_boxes = EXPECTED_BOXES - set(boxes)
    extra_boxes = set(boxes) - EXPECTED_BOXES
    if missing_boxes or extra_boxes:
        details = []
        if missing_boxes:
            boxes_text = ", ".join(str(box) for box in sorted(missing_boxes))
            details.append(f"empty boxes: {boxes_text}")
        if extra_boxes:
            boxes_text = ", ".join(str(box) for box in sorted(extra_boxes))
            details.append(f"unexpected boxes: {boxes_text}")
        raise ValueError(f"Each box must have at least one player; {'; '.join(details)}.")

    return path


def _validate_int(value: object, field_name: str, row_number: int) -> int:
    """Validate and return an integer CSV field."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Row {row_number} {field_name} must be an integer.") from exc


def _validate_numeric(value: object, field_name: str, row_number: int) -> float:
    """Validate and return a numeric CSV field."""
    try:
        return float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Row {row_number} {field_name} must be numeric.") from exc


def _validate_choice(
    value: object,
    field_name: str,
    allowed_values: set[str],
    row_number: int,
) -> str:
    """Validate and return a constrained text CSV field."""
    text = str(value).strip().lower()
    if text not in allowed_values:
        allowed = ", ".join(sorted(allowed_values))
        raise ValueError(f"Row {row_number} {field_name} must be one of: {allowed}.")
    return text


def validate_string_list(value: object, field_name: str) -> list[str]:
    """Validate that a field is a list of strings."""
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of strings.")

    if not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must contain only strings.")

    return value


def validate_locked_players(locked_players: object) -> list[str]:
    """Validate locked player names."""
    return validate_string_list(locked_players, "locked_players")


def validate_banned_players(banned_players: object) -> list[str]:
    """Validate banned player names."""
    return validate_string_list(banned_players, "banned_players")


def validate_banned_teams(banned_teams: object) -> list[str]:
    """Validate banned team names."""
    return validate_string_list(banned_teams, "banned_teams")


def validate_preferred_teams(preferred_teams: object) -> list[str]:
    """Validate preferred team codes."""
    return validate_string_list(preferred_teams, "preferred_teams")


def validate_preferences(
    risk_mode: str,
    strategy: str,
    csv_path: str | Path,
    locked_players: object,
    banned_teams: object,
    banned_players: object | None = None,
    preferred_teams: object | None = None,
) -> dict[str, object]:
    """Validate all preference inputs and return normalized values."""
    validated_risk_mode = validate_risk_mode(risk_mode)
    validated_strategy = validate_strategy(strategy)
    validated_csv_path = validate_csv_path(csv_path)
    validated_locked_players = validate_locked_players(locked_players)
    validated_banned_players = validate_banned_players(banned_players or [])
    validated_banned_teams = validate_banned_teams(banned_teams)
    validated_preferred_teams = validate_preferred_teams(preferred_teams or [])
    validate_csv_schema(validated_csv_path)
    return {
        "risk_mode": validated_risk_mode,
        "strategy": validated_strategy,
        "csv_path": validated_csv_path,
        "locked_players": validated_locked_players,
        "banned_players": validated_banned_players,
        "banned_teams": validated_banned_teams,
        "preferred_teams": validated_preferred_teams,
    }

"""Score calculation helpers."""

from collections.abc import Mapping


RISK_PENALTIES_BY_MODE = {
    "safe": {
        "low": 0.0,
        "medium": 4.0,
        "high": 9.0,
    },
    "balanced": {
        "low": 0.0,
        "medium": 2.0,
        "high": 5.0,
    },
    "risky": {
        "low": 0.0,
        "medium": 0.5,
        "high": 1.5,
    },
}

INJURY_PENALTIES = {
    "healthy": 0.0,
    "questionable": 8.0,
    "out": 25.0,
}

LOCKED_PLAYER_BONUS = 10.0
PREFERRED_TEAM_BONUS = 3.0
POPULARITY_WEIGHT = 10.0
DEFAULT_POPULARITY = 0.5
DEFAULT_PLAYER_RISK = "low"


def _as_float(value: object, field_name: str) -> float:
    """Convert a numeric field to float with a clear error message."""
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric.") from exc


def _get_text(row: Mapping[str, object], field_name: str, default: str = "") -> str:
    """Return a normalized text field from a player row."""
    value = row.get(field_name, default)
    if value is None:
        return default
    return str(value).strip()


def score_player(player_row: Mapping[str, object], preferences: Mapping[str, object]) -> float:
    """Score one player using a small explainable formula.

    Formula:
    projected points
    - risk penalty for the selected risk mode
    - injury penalty
    +/- popularity adjustment based on strategy
    + preferred team bonus
    + locked player bonus
    """
    if "projected_points" not in player_row:
        raise ValueError("player_row must include projected_points.")

    risk_mode = preferences.get("risk_mode", "balanced")
    if risk_mode not in RISK_PENALTIES_BY_MODE:
        allowed = ", ".join(sorted(RISK_PENALTIES_BY_MODE))
        raise ValueError(f"risk_mode must be one of: {allowed}.")

    strategy = preferences.get("strategy", "balanced")
    if strategy not in {"chalk", "balanced", "contrarian"}:
        raise ValueError("strategy must be one of: balanced, chalk, contrarian.")

    projected_points = _as_float(player_row["projected_points"], "projected_points")
    score = projected_points

    player_risk = _get_text(player_row, "risk", DEFAULT_PLAYER_RISK).lower()
    risk_penalty = RISK_PENALTIES_BY_MODE[risk_mode].get(player_risk, 0.0)
    score -= risk_penalty

    injury_status = _get_text(player_row, "injury_status", "healthy").lower()
    score -= INJURY_PENALTIES.get(injury_status, 0.0)

    popularity = _as_float(player_row.get("popularity", DEFAULT_POPULARITY), "popularity")
    popularity = max(0.0, min(1.0, popularity))
    if strategy == "chalk":
        score += popularity * POPULARITY_WEIGHT
    elif strategy == "contrarian":
        score += (1.0 - popularity) * POPULARITY_WEIGHT

    player_team = _get_text(player_row, "team")
    preferred_teams = preferences.get("preferred_teams", [])
    if player_team in preferred_teams:
        score += PREFERRED_TEAM_BONUS

    player_name = _get_text(player_row, "name")
    locked_players = preferences.get("locked_players", [])
    if player_name in locked_players:
        score += LOCKED_PLAYER_BONUS

    return round(score, 2)


def calculate_score(player):
    """Backward-compatible placeholder wrapper for older code paths."""
    return score_player(player, {"risk_mode": "balanced", "strategy": "balanced", "locked_players": []})

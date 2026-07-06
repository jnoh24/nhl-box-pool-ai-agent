"""Helpers for preparing uploaded NHL box pool CSV files."""

from collections.abc import Iterable

import pandas as pd


REQUIRED_COLUMNS = ("box", "name", "team")
OPTIONAL_COLUMNS = (
    "player_id",
    "position",
    "projected_points",
    "risk",
    "injury_status",
    "popularity",
    "salary",
)


def load_uploaded_pool(file) -> pd.DataFrame:
    """Load and normalize a user-uploaded CSV file."""
    return normalize_pool_dataframe(pd.read_csv(file))


def normalize_pool_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize upload columns and fill only safe non-performance defaults."""
    normalized = df.copy()
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]

    validate_minimum_schema(normalized)

    if "player_id" not in normalized.columns:
        normalized["player_id"] = range(1, len(normalized) + 1)
    else:
        normalized["player_id"] = _fill_missing_by_row_number(normalized["player_id"])

    if "position" not in normalized.columns:
        normalized["position"] = "UNKNOWN"
    else:
        normalized["position"] = normalized["position"].fillna("UNKNOWN").replace("", "UNKNOWN")

    if "injury_status" not in normalized.columns:
        normalized["injury_status"] = "unknown"
    else:
        normalized["injury_status"] = (
            normalized["injury_status"].fillna("unknown").replace("", "unknown")
        )

    if "salary" not in normalized.columns:
        normalized["salary"] = 0
    else:
        normalized["salary"] = normalized["salary"].fillna(0).replace("", 0)

    return normalized


def validate_minimum_schema(df: pd.DataFrame) -> None:
    """Require only the columns needed to identify players and boxes."""
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Uploaded CSV is missing required columns: {missing}.")


def check_optimization_readiness(df: pd.DataFrame) -> dict[str, object]:
    """Return whether an uploaded pool has enough data for optimization."""
    missing_required = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    missing_optional = [
        column for column in OPTIONAL_COLUMNS if column not in df.columns or _column_is_blank(df[column])
    ]

    has_projected_points = "projected_points" not in missing_optional
    has_popularity = "popularity" not in missing_optional
    has_risk = "risk" not in missing_optional

    disabled_features = []
    messages = []

    if missing_required:
        messages.append(
            "Missing required columns: " + ", ".join(missing_required) + "."
        )

    if not has_projected_points:
        messages.append("Missing projected_points; optimization cannot run.")

    if not has_popularity:
        disabled_features.append("chalk_and_contrarian_strategy")
        messages.append("Missing popularity; chalk and contrarian strategy are disabled.")

    if not has_risk:
        disabled_features.append("risk_based_modes")
        messages.append("Missing risk; risk-based modes are disabled.")

    if not messages:
        messages.append("Dataset is ready for optimization.")

    return {
        "optimization_ready": not missing_required and has_projected_points,
        "missing_required_columns": missing_required,
        "missing_optional_columns": missing_optional,
        "disabled_features": disabled_features,
        "can_use_chalk_contrarian": has_popularity,
        "can_use_risk_modes": has_risk,
        "messages": messages,
    }


def _fill_missing_by_row_number(values: pd.Series) -> pd.Series:
    """Fill blank player IDs with their one-based row number."""
    filled = values.copy()
    for row_index, value in filled.items():
        if pd.isna(value) or value == "":
            filled.at[row_index] = row_index + 1
    return filled


def _column_is_blank(values: Iterable[object]) -> bool:
    """Return whether a column has no meaningful values."""
    for value in values:
        if not pd.isna(value) and str(value).strip() != "":
            return False
    return True

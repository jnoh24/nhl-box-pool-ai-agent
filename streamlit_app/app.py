"""Streamlit UI for the NHL Box Pool Preference Agent."""

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.preference_parser import parse_preferences
from tools.data_intake import (
    check_optimization_readiness,
    load_uploaded_pool,
)
from tools.optimizer import DEFAULT_CSV_PATH, optimize_lineup


st.set_page_config(page_title="NHL Box Pool Preference Agent")

st.title("NHL Box Pool Preference Agent")


@st.cache_data
def load_demo_pool(csv_path: str):
    """Load the bundled demo pool through the same intake path as uploads."""
    with Path(csv_path).open(newline="", encoding="utf-8") as csv_file:
        return load_uploaded_pool(csv_file)


def format_list(values: object) -> list[object]:
    """Format list-like preference values for display."""
    if not values:
        return []
    if isinstance(values, list):
        return values
    return [str(values)]


def merge_unique(parsed_values: object, ui_values: list[str]) -> list[str]:
    """Merge parsed and UI-selected preference lists while preserving order."""
    merged: list[str] = []
    for value in [*format_list(parsed_values), *ui_values]:
        text = str(value)
        if text not in merged:
            merged.append(text)
    return merged


def box_sort_key(player: dict[str, object]) -> tuple[int, object]:
    """Sort numeric boxes naturally and fall back to text ordering."""
    box = str(player["box"])
    if box.isdigit():
        return (0, int(box))
    return (1, box)


def clear_invalid_selection(key: str, valid_options: list[str]) -> None:
    """Remove stale selections when the active dataset changes."""
    if key not in st.session_state:
        return

    valid = set(valid_options)
    st.session_state[key] = [
        value for value in st.session_state[key] if value in valid
    ]


uploaded_csv = st.file_uploader("Upload box pool CSV", type=["csv"])

try:
    if uploaded_csv is None:
        pool_df = load_demo_pool(str(DEFAULT_CSV_PATH))
        active_dataset_name = f"demo dataset: {DEFAULT_CSV_PATH}"
    else:
        pool_df = load_uploaded_pool(uploaded_csv)
        active_dataset_name = f"uploaded dataset: {uploaded_csv.name}"
except ValueError as exc:
    st.error(str(exc))
    st.stop()

st.caption(f"Using {active_dataset_name}")

readiness = check_optimization_readiness(pool_df)
available_teams = sorted(str(team) for team in pool_df["team"].dropna().unique())
available_players = sorted(str(name) for name in pool_df["name"].dropna().unique())
clear_invalid_selection("preferred_teams", available_teams)
clear_invalid_selection("banned_teams", available_teams)
clear_invalid_selection("locked_players", available_players)
clear_invalid_selection("banned_players", available_players)

st.subheader("Dataset Preview")
st.dataframe(pool_df.head(20), hide_index=True, use_container_width=True)

st.subheader("Readiness Report")
st.write(
    {
        "ready_for_optimization": readiness["optimization_ready"],
        "missing_projected_points": "projected_points"
        in readiness["missing_optional_columns"],
        "missing_risk": "risk" in readiness["missing_optional_columns"],
        "missing_popularity": "popularity" in readiness["missing_optional_columns"],
    }
)
for message in readiness["messages"]:
    st.caption(message)

can_optimize = bool(readiness["optimization_ready"])
if not can_optimize:
    st.warning(
        "This box pool is valid, but optimization requires projected_points. "
        "Please upload a CSV with projected_points or use the demo dataset."
    )

risk_options = ["safe", "balanced", "risky"]
strategy_options = ["chalk", "balanced", "contrarian"]
if not readiness["can_use_risk_modes"]:
    risk_options = ["balanced"]
if not readiness["can_use_chalk_contrarian"]:
    strategy_options = ["balanced"]

user_text = st.text_area(
    "Natural language prompt",
    value="",
    height=120,
    placeholder="Example: I want a safe lineup, lock McDavid, avoid Toronto, and prefer Colorado.",
)

control_col_one, control_col_two = st.columns(2)
with control_col_one:
    preferred_teams = st.multiselect(
        "Preferred teams",
        available_teams,
        key="preferred_teams",
    )
    locked_players = st.multiselect(
        "Locked players",
        available_players,
        key="locked_players",
    )
    risk_mode = st.selectbox("Risk mode", risk_options, index=risk_options.index("balanced"))
with control_col_two:
    banned_teams = st.multiselect(
        "Banned teams",
        available_teams,
        key="banned_teams",
    )
    banned_players = st.multiselect(
        "Banned players",
        available_players,
        key="banned_players",
    )
    strategy = st.selectbox(
        "Strategy",
        strategy_options,
        index=strategy_options.index("balanced"),
    )

optimize_clicked = st.button("Optimize", type="primary")

if optimize_clicked:
    if not can_optimize:
        st.warning(
            "This box pool is valid, but optimization requires projected_points. "
            "Please upload a CSV with projected_points or use the demo dataset."
        )
        st.stop()

    try:
        parsed_preferences = parse_preferences(user_text)
        preferences = {
            "locked_players": merge_unique(
                parsed_preferences.get("locked_players", []),
                locked_players,
            ),
            "banned_teams": merge_unique(
                parsed_preferences.get("banned_teams", []),
                banned_teams,
            ),
            "banned_players": merge_unique(
                parsed_preferences.get("banned_players", []),
                banned_players,
            ),
            "preferred_teams": merge_unique(
                parsed_preferences.get("preferred_teams", []),
                preferred_teams,
            ),
            "risk_mode": risk_mode,
            "strategy": strategy,
            "avoid_expensive": parsed_preferences.get("avoid_expensive", False),
        }
        result = optimize_lineup(preferences, pool_df=pool_df)
    except ValueError as exc:
        st.error(str(exc))
    else:
        st.subheader("Interpreted Preferences")
        st.write(
            {
                "locked_players": format_list(preferences["locked_players"]),
                "banned_players": format_list(preferences["banned_players"]),
                "banned_teams": format_list(preferences["banned_teams"]),
                "preferred_teams": format_list(preferences["preferred_teams"]),
                "risk_mode": preferences["risk_mode"],
                "strategy": preferences["strategy"],
                "avoid_expensive": preferences["avoid_expensive"],
            }
        )

        st.subheader("Recommended Lineup")
        lineup_rows = [
            {
                "box": player["box"],
                "name": player["name"],
                "team": player["team"],
                "position": player["position"],
                "projected_points": player["projected_points"],
                "risk": player["risk"],
                "injury_status": player["injury_status"],
                "popularity": player["popularity"],
                "salary": player["salary"],
                "adjusted_score": player["adjusted_score"],
            }
            for player in sorted(result["lineup"], key=box_sort_key)
        ]
        st.dataframe(lineup_rows, hide_index=True, use_container_width=True)

        projected_col, adjusted_col = st.columns(2)
        projected_col.metric(
            "Total Projected Points",
            result["total_projected_points"],
        )
        adjusted_col.metric(
            "Total Adjusted Score",
            result["total_adjusted_score"],
        )

        st.subheader("Explanation")
        st.write(result["tradeoff_explanation"])

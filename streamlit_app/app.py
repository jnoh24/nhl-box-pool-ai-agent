"""Streamlit UI for the NHL Box Pool Preference Agent."""

import csv
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.preference_parser import parse_preferences
from tools.optimizer import DEFAULT_CSV_PATH, optimize_lineup


st.set_page_config(page_title="NHL Box Pool Preference Agent")

st.title("NHL Box Pool Preference Agent")


@st.cache_data
def load_player_pool(csv_path: str) -> list[dict[str, str]]:
    """Load player data for UI controls."""
    with Path(csv_path).open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


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


player_pool = load_player_pool(str(DEFAULT_CSV_PATH))
available_teams = sorted({player["team"] for player in player_pool})
available_players = sorted({player["name"] for player in player_pool})

user_text = st.text_area(
    "Natural language prompt",
    value="",
    height=120,
    placeholder="Example: I want a safe lineup, lock McDavid, avoid Toronto, and prefer Colorado.",
)

control_col_one, control_col_two = st.columns(2)
with control_col_one:
    preferred_teams = st.multiselect("Preferred teams", available_teams)
    locked_players = st.multiselect("Locked players", available_players)
    risk_mode = st.selectbox("Risk mode", ["safe", "balanced", "risky"], index=1)
with control_col_two:
    banned_teams = st.multiselect("Banned teams", available_teams)
    banned_players = st.multiselect("Banned players", available_players)
    strategy = st.selectbox("Strategy", ["chalk", "balanced", "contrarian"], index=1)

optimize_clicked = st.button("Optimize", type="primary")

if optimize_clicked:
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
        result = optimize_lineup(preferences)
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

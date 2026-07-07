"""Streamlit UI for the NHL Box Pool Preference Agent."""

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.preference_parser import extract_parsed_preferences
from streamlit_app.mcp_client import (
    MCPClientError,
    call_optimize_lineup,
    call_parse_preferences,
)
from streamlit_app.team_background import render_team_background_selector
from tools.data_intake import (
    check_optimization_readiness,
    load_uploaded_pool,
)
from tools.optimizer import DEFAULT_CSV_PATH


st.set_page_config(page_title="NHL Box Pool Preference Agent")

favorite_team = render_team_background_selector()

st.title("NHL Box Pool Preference Agent")
st.caption(f"Background theme: {favorite_team}")
st.info(
    "Upload your NHL box pool CSV or use the demo dataset. At minimum, include "
    "box, name, and team; add projected_points to enable optimization. "
    "Optional risk and popularity columns unlock safe/risky and chalk/contrarian "
    "strategy modes. Then use the prompt and preference controls to lock, ban, "
    "prioritize, and optimize your lineup."
)


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


def apply_clarification(
    preferences: dict[str, object],
    answer: str,
) -> tuple[dict[str, object], str]:
    """Apply a clarification answer to parsed preferences."""
    updated = {key: value for key, value in preferences.items()}
    explanation = f"You clarified: {answer}."

    if answer.startswith("Prioritize "):
        team_name = answer.removeprefix("Prioritize ")
        team_lookup = {
            "Colorado": "COL",
            "Edmonton": "EDM",
            "Toronto": "TOR",
            "Winnipeg": "WPG",
            "Boston": "BOS",
        }
        team_code = team_lookup.get(team_name)
        if team_code is not None:
            preferred_teams = format_list(updated.get("preferred_teams", []))
            if team_code not in preferred_teams:
                preferred_teams.append(team_code)
            updated["preferred_teams"] = preferred_teams
            explanation = (
                f"You asked to prioritize {team_name} players rather than requiring them. "
                "The optimizer treated that as a moderate preferred-team bonus."
            )
    elif answer in {"High upside", "Use risky mode"}:
        updated["risk_mode"] = "risky"
        explanation = "You clarified that you want more upside, so I used risky mode."
    elif answer in {"Use safe mode"}:
        updated["risk_mode"] = "safe"
        explanation = "You clarified that you want safer picks, so I used safe mode."
    elif answer in {"Contrarian picks"}:
        updated["strategy"] = "contrarian"
        explanation = "You clarified that unique means contrarian, so I favored lower-popularity picks."
    elif answer in {"Balanced lineup", "Stay balanced", "Choose balanced lineup"}:
        updated["risk_mode"] = "balanced"
        updated["strategy"] = "balanced"
        explanation = "You clarified that I should keep the recommendation balanced."

    return updated, explanation


def build_preferences(
    parsed_preferences: dict[str, object],
    locked_players: list[str],
    banned_teams: list[str],
    banned_players: list[str],
    preferred_teams: list[str],
    risk_mode: str,
    strategy: str,
) -> dict[str, object]:
    """Merge parsed preferences with UI-selected preferences."""
    return {
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
pool_records = pool_df.to_dict(orient="records")
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
        parse_result = call_parse_preferences(user_text)
        parsed_preferences = extract_parsed_preferences(parse_result)
        preferences = build_preferences(
            parsed_preferences,
            locked_players,
            banned_teams,
            banned_players,
            preferred_teams,
            risk_mode,
            strategy,
        )
        if parse_result["clarification_needed"]:
            st.session_state["pending_clarification"] = {
                "question": parse_result["clarification_question"],
                "options": parse_result["clarification_options"],
                "preferences": preferences,
            }
        else:
            st.session_state.pop("pending_clarification", None)
            st.session_state.pop("clarification_explanation", None)
    except (MCPClientError, ValueError) as exc:
        st.error(str(exc))
        st.stop()

if "pending_clarification" in st.session_state:
    pending = st.session_state["pending_clarification"]
    st.subheader("Clarification Needed")
    st.write(pending["question"])
    clarification_answer = st.selectbox(
        "Choose how to interpret this request",
        pending["options"],
    )
    if st.button("Apply clarification and optimize", type="primary"):
        preferences, clarification_explanation = apply_clarification(
            pending["preferences"],
            clarification_answer,
        )
        st.session_state["clarification_explanation"] = clarification_explanation
        st.session_state.pop("pending_clarification", None)
        try:
            result = call_optimize_lineup(preferences, pool_records)
        except (MCPClientError, ValueError) as exc:
            st.error(str(exc))
            st.stop()
    else:
        st.stop()
elif optimize_clicked:
    try:
        result = call_optimize_lineup(preferences, pool_records)
    except (MCPClientError, ValueError) as exc:
        st.error(str(exc))
        st.stop()
else:
    result = None

if result is not None:
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

    if "clarification_explanation" in st.session_state:
        st.info(st.session_state["clarification_explanation"])

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

"""Sidebar-controlled NHL logo background for Streamlit apps."""

import streamlit as st


# Official transparent NHL logo assets. The three-letter codes match NHL team codes.
NHL_LOGOS = {
    "Anaheim Ducks": "https://assets.nhle.com/logos/nhl/svg/ANA_light.svg",
    "Boston Bruins": "https://assets.nhle.com/logos/nhl/svg/BOS_light.svg",
    "Buffalo Sabres": "https://assets.nhle.com/logos/nhl/svg/BUF_light.svg",
    "Calgary Flames": "https://assets.nhle.com/logos/nhl/svg/CGY_light.svg",
    "Carolina Hurricanes": "https://assets.nhle.com/logos/nhl/svg/CAR_light.svg",
    "Chicago Blackhawks": "https://assets.nhle.com/logos/nhl/svg/CHI_light.svg",
    "Colorado Avalanche": "https://assets.nhle.com/logos/nhl/svg/COL_light.svg",
    "Columbus Blue Jackets": "https://assets.nhle.com/logos/nhl/svg/CBJ_light.svg",
    "Dallas Stars": "https://assets.nhle.com/logos/nhl/svg/DAL_light.svg",
    "Detroit Red Wings": "https://assets.nhle.com/logos/nhl/svg/DET_light.svg",
    "Edmonton Oilers": "https://assets.nhle.com/logos/nhl/svg/EDM_light.svg",
    "Florida Panthers": "https://assets.nhle.com/logos/nhl/svg/FLA_light.svg",
    "Los Angeles Kings": "https://assets.nhle.com/logos/nhl/svg/LAK_light.svg",
    "Minnesota Wild": "https://assets.nhle.com/logos/nhl/svg/MIN_light.svg",
    "Montreal Canadiens": "https://assets.nhle.com/logos/nhl/svg/MTL_light.svg",
    "Nashville Predators": "https://assets.nhle.com/logos/nhl/svg/NSH_light.svg",
    "New Jersey Devils": "https://assets.nhle.com/logos/nhl/svg/NJD_light.svg",
    "New York Islanders": "https://assets.nhle.com/logos/nhl/svg/NYI_light.svg",
    "New York Rangers": "https://assets.nhle.com/logos/nhl/svg/NYR_light.svg",
    "Ottawa Senators": "https://assets.nhle.com/logos/nhl/svg/OTT_light.svg",
    "Philadelphia Flyers": "https://assets.nhle.com/logos/nhl/svg/PHI_light.svg",
    "Pittsburgh Penguins": "https://assets.nhle.com/logos/nhl/svg/PIT_light.svg",
    "San Jose Sharks": "https://assets.nhle.com/logos/nhl/svg/SJS_light.svg",
    "Seattle Kraken": "https://assets.nhle.com/logos/nhl/svg/SEA_light.svg",
    "St. Louis Blues": "https://assets.nhle.com/logos/nhl/svg/STL_light.svg",
    "Tampa Bay Lightning": "https://assets.nhle.com/logos/nhl/svg/TBL_light.svg",
    "Toronto Maple Leafs": "https://assets.nhle.com/logos/nhl/svg/TOR_light.svg",
    "Utah Mammoth": "https://assets.nhle.com/logos/nhl/svg/UTA_light.svg",
    "Vancouver Canucks": "https://assets.nhle.com/logos/nhl/svg/VAN_light.svg",
    "Vegas Golden Knights": "https://assets.nhle.com/logos/nhl/svg/VGK_light.svg",
    "Washington Capitals": "https://assets.nhle.com/logos/nhl/svg/WSH_light.svg",
    "Winnipeg Jets": "https://assets.nhle.com/logos/nhl/svg/WPG_light.svg",
}


def render_team_background_selector(default_team: str = "Toronto Maple Leafs") -> str:
    """Render a sidebar team selector and apply the selected logo background."""
    st.sidebar.markdown(
        """
        <div style="
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin: 0.35rem 0 0.75rem 0;
        ">
            <div style="
                width: 2rem;
                height: 2rem;
                border-radius: 999px;
                border: 1px solid rgba(49, 51, 63, 0.22);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.02rem;
            ">NHL</div>
            <div>
                <div style="font-weight: 700; line-height: 1.1;">Settings</div>
                <div style="font-size: 0.82rem; opacity: 0.72;">Change background</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    teams = sorted(NHL_LOGOS)
    default_index = teams.index(default_team) if default_team in teams else 0
    selected_team = st.sidebar.selectbox(
        "Favorite team",
        options=teams,
        index=default_index,
    )
    apply_team_background(NHL_LOGOS[selected_team])
    return selected_team


def apply_team_background(
    logo_url: str,
    opacity: float = 0.08,
    background_size: str = "52%",
) -> None:
    """Inject a faded fixed logo behind Streamlit app content.

    Increase or decrease `background_size` to resize the logo, for example
    "30%" for smaller or "55%" for larger.
    """
    st.markdown(
        f"""
        <style>
        [data-testid="stApp"] {{
            position: relative;
            background: #ffffff;
        }}

        [data-testid="stApp"]::before {{
            content: "";
            position: fixed;
            inset: 0;
            background-image: url("{logo_url}");
            background-repeat: no-repeat;
            background-position: center;
            background-size: {background_size};
            opacity: {opacity};
            z-index: 0;
            pointer-events: none;
        }}

        [data-testid="stHeader"],
        [data-testid="stSidebar"],
        [data-testid="stAppViewContainer"],
        [data-testid="stToolbar"] {{
            position: relative;
            z-index: 2;
        }}

        [data-testid="stAppViewContainer"] > .main {{
            position: relative;
            z-index: 1;
            background: transparent;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

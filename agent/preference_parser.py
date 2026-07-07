"""Rule-based preference parser.

This module will convert natural language preferences into structured
constraints for the optimizer.
"""

import re


DEFAULT_PREFERENCES = {
    "locked_players": [],
    "banned_players": [],
    "banned_teams": [],
    "risk_mode": "balanced",
    "strategy": "balanced",
    "avoid_expensive": False,
    "preferred_teams": [],
}

DEFAULT_PARSE_RESULT = {
    "parsed_preferences": DEFAULT_PREFERENCES,
    "clarification_needed": False,
    "clarification_question": None,
    "clarification_options": [],
}

PLAYER_ALIASES = {
    "connor mcdavid": "Connor McDavid",
    "mcdavid": "Connor McDavid",
    "nathan mackinnon": "Nathan MacKinnon",
    "mackinnon": "Nathan MacKinnon",
    "auston matthews": "Auston Matthews",
    "matthews": "Auston Matthews",
    "david pastrnak": "David Pastrnak",
    "pastrnak": "David Pastrnak",
    "sidney crosby": "Sidney Crosby",
    "crosby": "Sidney Crosby",
    "cale makar": "Cale Makar",
    "makar": "Cale Makar",
    "adam fox": "Adam Fox",
    "fox": "Adam Fox",
    "igor shesterkin": "Igor Shesterkin",
    "shesterkin": "Igor Shesterkin",
    "connor hellebuyck": "Connor Hellebuyck",
    "hellebuyck": "Connor Hellebuyck",
}

TEAM_ALIASES = {
    "tor": "TOR",
    "toronto": "TOR",
    "maple leafs": "TOR",
    "leafs": "TOR",
    "edm": "EDM",
    "edmonton": "EDM",
    "oilers": "EDM",
    "col": "COL",
    "colorado": "COL",
    "avalanche": "COL",
    "avs": "COL",
    "bos": "BOS",
    "boston": "BOS",
    "bruins": "BOS",
    "nyr": "NYR",
    "rangers": "NYR",
    "wpg": "WPG",
    "winnipeg": "WPG",
    "jets": "WPG",
}

LOCK_PATTERNS = (
    "i really want",
    "i want",
    "want",
    "lock",
    "locked",
    "must have",
    "include",
)

BAN_PATTERNS = (
    "avoid",
    "ban",
    "banned",
    "no",
    "exclude",
    "fade",
    "don't want",
    "do not want",
    "dont want",
    "don't want any players from",
    "do not want any players from",
    "dont want any players from",
    "don't want players from",
    "do not want players from",
    "dont want players from",
)

PREFERRED_TEAM_PATTERNS = (
    "as many",
    "most",
    "prioritize",
    "prefer",
    "want more",
    "i want more",
    "players from",
    "want players from",
    "i want players from",
    "really want players from",
    "i really want players from",
    "want",
    "i want",
    "really want",
    "i really want",
)

CONTRARIAN_TERMS = (
    "contrarian",
    "sleeper",
    "unique",
    "different",
)

CHALK_TERMS = (
    "chalk",
    "popular",
    "obvious picks",
)

SAFE_TERMS = (
    "safe",
    "low risk",
    "consistent",
)

RISKY_TERMS = (
    "risky",
    "high upside",
    "boom or bust",
)

AVOID_EXPENSIVE_TERMS = (
    "avoid expensive players",
    "cheap",
    "low salary",
)

AMBIGUOUS_RISK_TERMS = (
    "don't mind taking some risks",
    "do not mind taking some risks",
    "some risks",
)

AMBIGUOUS_FUN_TERMS = (
    "fun lineup",
    "fun team",
)


def _normalize(text: str) -> str:
    """Normalize text for simple matching."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def _contains_word(text: str, term: str) -> bool:
    """Return whether a term appears as a phrase or word-like token."""
    pattern = rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _append_once(values: list[str], value: str) -> None:
    """Append a value while preserving order and avoiding duplicates."""
    if value not in values:
        values.append(value)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    """Return whether any term appears as a phrase or word-like token."""
    return any(_contains_word(text, term) for term in terms)


def _mentioned_after_signal(text: str, alias: str, signals: tuple[str, ...]) -> bool:
    """Check that an alias appears after a nearby intent signal."""
    return any(_contains_word(text, signal) and _contains_word(text, alias) for signal in signals)


def _team_aliases_by_mention_order(text: str) -> list[tuple[int, str, str]]:
    """Return team aliases sorted by where they first appear in the text."""
    mentions = []
    for alias, team_code in TEAM_ALIASES.items():
        pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
        match = re.search(pattern, text)
        if match is not None:
            mentions.append((match.start(), alias, team_code))
    return sorted(mentions)


def _nearest_signal_before(
    text: str,
    alias_position: int,
    signals: tuple[str, ...],
) -> int | None:
    """Return the nearest signal that appears before an alias."""
    positions = []
    for signal in signals:
        pattern = rf"(?<![a-z0-9]){re.escape(signal)}(?![a-z0-9])"
        positions.extend(
            match.start()
            for match in re.finditer(pattern, text)
            if match.start() <= alias_position
        )
    if not positions:
        return None
    return max(positions)


def _has_negated_want_before(text: str, alias_position: int) -> bool:
    """Return whether a don't-want phrase appears before a team alias."""
    negated_wants = (
        "don't want",
        "do not want",
        "dont want",
    )
    return _nearest_signal_before(text, alias_position, negated_wants) is not None


def _default_preferences() -> dict[str, object]:
    """Return a fresh default preferences dictionary."""
    return {
        "locked_players": [],
        "banned_players": [],
        "banned_teams": [],
        "risk_mode": "balanced",
        "strategy": "balanced",
        "avoid_expensive": False,
        "preferred_teams": [],
    }


def _parse_result(
    preferences: dict[str, object],
    question: str | None = None,
    options: list[str] | None = None,
) -> dict[str, object]:
    """Build the parser response envelope."""
    return {
        "parsed_preferences": preferences,
        "clarification_needed": question is not None,
        "clarification_question": question,
        "clarification_options": options or [],
    }


def _team_name_for_question(team_code: str) -> str:
    """Return a readable team name for clarification prompts."""
    names = {
        "COL": "Colorado",
        "EDM": "Edmonton",
        "TOR": "Toronto",
        "WPG": "Winnipeg",
        "BOS": "Boston",
        "NYR": "Rangers",
    }
    return names.get(team_code, team_code)


def _ambiguous_team_question(team_code: str) -> tuple[str, list[str]]:
    """Return a clarification question for an uncertain team preference."""
    team_name = _team_name_for_question(team_code)
    return (
        f"You mentioned {team_name} players. Would you like me to:\n"
        f"1. Prioritize {team_name} players whenever possible\n"
        f"2. Require a minimum number of {team_name} players\n"
        f"3. Lock specific {team_name} players?",
        [
            f"Prioritize {team_name}",
            "Require minimum players",
            "Lock specific players",
        ],
    )


def _find_ambiguous_team_code(text: str) -> str | None:
    """Detect team mentions where intent is too vague to optimize immediately."""
    if _contains_word(text, "lots"):
        for _, _alias, team_code in _team_aliases_by_mention_order(text):
            return team_code

    for alias_position, _alias, team_code in _team_aliases_by_mention_order(text):
        like_position = _nearest_signal_before(text, alias_position, ("i like", "like"))
        if like_position is not None:
            return team_code

    return None


def _clarification_for_text(text: str) -> tuple[str, list[str]] | None:
    """Return a clarification prompt for ambiguous requests."""
    team_code = _find_ambiguous_team_code(text)
    if team_code is not None:
        return _ambiguous_team_question(team_code)

    if _contains_any(text, AMBIGUOUS_FUN_TERMS):
        return (
            "When you say a fun lineup, what should I optimize for?",
            ["High upside", "Contrarian picks", "Balanced lineup"],
        )

    if _contains_word(text, "unique team"):
        return (
            "When you say a unique team, would you like me to favor contrarian picks or stack one team?",
            ["Contrarian picks", "Stack one team", "Balanced lineup"],
        )

    if _contains_any(text, AMBIGUOUS_RISK_TERMS):
        return (
            "How much risk should I take?",
            ["Use risky mode", "Stay balanced", "Use safe mode"],
        )

    if _contains_word(text, "stack one team"):
        return (
            "Which stacking approach should I use?",
            ["Prioritize a preferred team", "Choose balanced lineup"],
        )

    return None


def extract_parsed_preferences(parse_result: dict[str, object]) -> dict[str, object]:
    """Return optimizer-ready preferences from a parser response."""
    if "parsed_preferences" in parse_result:
        return parse_result["parsed_preferences"]  # type: ignore[return-value]
    return parse_result


def parse_preferences(user_text: str) -> dict[str, object]:
    """Parse natural language preferences into constraints.

    This parser is intentionally rule-based. It does not call an LLM API.
    """
    if not isinstance(user_text, str):
        raise ValueError("user_text must be a string.")

    text = _normalize(user_text)
    preferences = _default_preferences()

    if not text:
        return _parse_result(preferences)

    clarification = _clarification_for_text(text)
    if clarification is not None:
        question, options = clarification
        return _parse_result(preferences, question, options)

    if _contains_any(text, SAFE_TERMS):
        preferences["risk_mode"] = "safe"
    elif _contains_any(text, RISKY_TERMS):
        preferences["risk_mode"] = "risky"

    if _contains_any(text, CONTRARIAN_TERMS):
        preferences["strategy"] = "contrarian"
    elif _contains_any(text, CHALK_TERMS):
        preferences["strategy"] = "chalk"

    if _contains_any(text, AVOID_EXPENSIVE_TERMS):
        preferences["avoid_expensive"] = True

    for alias, player_name in PLAYER_ALIASES.items():
        alias_position = text.find(alias)
        if alias_position == -1:
            continue

        ban_position = _nearest_signal_before(text, alias_position, BAN_PATTERNS)
        lock_position = _nearest_signal_before(text, alias_position, LOCK_PATTERNS)
        if _has_negated_want_before(text, alias_position) or (
            ban_position is not None and (lock_position is None or ban_position >= lock_position)
        ):
            _append_once(preferences["banned_players"], player_name)
        elif lock_position is not None:
            _append_once(preferences["locked_players"], player_name)

    for alias_position, alias, team_code in _team_aliases_by_mention_order(text):
        ban_position = _nearest_signal_before(text, alias_position, BAN_PATTERNS)
        preferred_position = _nearest_signal_before(
            text,
            alias_position,
            PREFERRED_TEAM_PATTERNS,
        )
        if _has_negated_want_before(text, alias_position) or (
            ban_position is not None
            and (preferred_position is None or ban_position > preferred_position)
        ):
            _append_once(preferences["banned_teams"], team_code)
        elif preferred_position is not None:
            _append_once(preferences["preferred_teams"], team_code)

    return _parse_result(preferences)

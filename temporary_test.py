from tools.optimizer import optimize_lineup

prefs = {
    "locked_players": ["Connor McDavid"],
    "banned_teams": ["TOR"],
    "risk_mode": "balanced",
    "strategy": "contrarian"
}

print(optimize_lineup(prefs))



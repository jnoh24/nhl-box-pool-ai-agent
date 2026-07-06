"""Simple box pool advisor agent.

This module provides a small orchestration class that can later be wrapped by
Google ADK. For now it coordinates parsing, optimization, and response writing.
"""

from collections.abc import Callable, Mapping
from pathlib import Path

from agent.preference_parser import parse_preferences
from tools.optimizer import DEFAULT_CSV_PATH, optimize_lineup


class BoxPoolAdvisorAgent:
    """Conversational advisor for NHL box pool lineup recommendations."""

    def __init__(
        self,
        csv_path: str | Path = DEFAULT_CSV_PATH,
        parser: Callable[[str], dict[str, object]] = parse_preferences,
        optimizer: Callable[[Mapping[str, object], str | Path], dict[str, object]] = optimize_lineup,
    ) -> None:
        self.csv_path = csv_path
        self.parser = parser
        self.optimizer = optimizer

    def advise(self, user_text: str) -> str:
        """Return a conversational recommendation for a user's request."""
        recommendation = self.recommend(user_text)
        return recommendation["response"]

    def recommend(self, user_text: str) -> dict[str, object]:
        """Return structured recommendation data for apps and tools."""
        preferences = self.parser(user_text)
        result = self.optimizer(preferences, self.csv_path)
        response = self._format_response(preferences, result)
        return {
            "preferences": preferences,
            "lineup": result["lineup"],
            "total_projected_points": result["total_projected_points"],
            "total_adjusted_score": result["total_adjusted_score"],
            "tradeoff_explanation": result["tradeoff_explanation"],
            "response": response,
        }

    def _format_response(
        self,
        preferences: Mapping[str, object],
        result: Mapping[str, object],
    ) -> str:
        """Format optimizer output into a readable recommendation."""
        lineup_lines = [
            (
                f"- Box {player['box']}: {player['name']} ({player['team']}, "
                f"{player['position']}) - {player['projected_points']} projected, "
                f"{player['adjusted_score']} adjusted"
            )
            for player in result["lineup"]
        ]

        return "\n".join(
            [
                "Here is the lineup I recommend based on your preferences.",
                "",
                "Interpreted preferences:",
                f"- Locked players: {self._format_list(preferences['locked_players'])}",
                f"- Banned teams: {self._format_list(preferences['banned_teams'])}",
                f"- Risk mode: {preferences['risk_mode']}",
                f"- Strategy: {preferences['strategy']}",
                "",
                "Recommended lineup:",
                *lineup_lines,
                "",
                f"Total projected points: {result['total_projected_points']}",
                f"Total adjusted score: {result['total_adjusted_score']}",
                "",
                f"Tradeoffs: {result['tradeoff_explanation']}",
                "",
                "Follow-up question: Do you want to lock any must-have players before I refine it?",
            ]
        )

    @staticmethod
    def _format_list(values: object) -> str:
        """Format preference lists for display."""
        if not values:
            return "none"
        return ", ".join(str(value) for value in values)


def create_agent() -> BoxPoolAdvisorAgent:
    """Create the simple box pool advisor agent."""
    return BoxPoolAdvisorAgent()

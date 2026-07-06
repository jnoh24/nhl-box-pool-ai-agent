"""Tests for the box pool advisor agent."""

from agent.main_agent import BoxPoolAdvisorAgent, create_agent


def test_box_pool_advisor_agent_returns_recommendation_sections():
    agent = BoxPoolAdvisorAgent()

    response = agent.advise("Safe lineup, I really want McDavid and avoid Toronto")

    assert "Interpreted preferences:" in response
    assert "Locked players: Connor McDavid" in response
    assert "Banned teams: TOR" in response
    assert "Risk mode: safe" in response
    assert "Strategy: balanced" in response
    assert "Recommended lineup:" in response
    assert "Connor McDavid" in response
    assert "Total projected points:" in response
    assert "Tradeoffs:" in response
    assert "Follow-up question:" in response


def test_box_pool_advisor_agent_uses_parser_and_optimizer_dependencies():
    def parser(user_text):
        assert user_text == "test request"
        return {
            "locked_players": [],
            "banned_teams": [],
            "risk_mode": "risky",
            "strategy": "chalk",
        }

    def optimizer(preferences, csv_path):
        assert preferences["risk_mode"] == "risky"
        assert preferences["strategy"] == "chalk"
        assert str(csv_path) == "data/sample_pool.csv"
        return {
            "lineup": [
                {
                    "box": "1",
                    "name": "Connor McDavid",
                    "team": "EDM",
                    "position": "C",
                    "projected_points": 120.0,
                    "adjusted_score": 129.5,
                }
            ],
            "total_projected_points": 120.0,
            "total_adjusted_score": 129.5,
            "tradeoff_explanation": "Box 1: selected Connor McDavid.",
        }

    agent = BoxPoolAdvisorAgent(parser=parser, optimizer=optimizer)

    response = agent.advise("test request")

    assert "Risk mode: risky" in response
    assert "Strategy: chalk" in response
    assert "Connor McDavid" in response


def test_box_pool_advisor_agent_recommend_returns_structured_data():
    agent = BoxPoolAdvisorAgent()

    recommendation = agent.recommend("I want a safe lineup and chalk picks")

    assert recommendation["preferences"]["risk_mode"] == "safe"
    assert recommendation["preferences"]["strategy"] == "chalk"
    assert recommendation["lineup"]
    assert "total_projected_points" in recommendation
    assert "total_adjusted_score" in recommendation
    assert "tradeoff_explanation" in recommendation
    assert "response" in recommendation


def test_create_agent_returns_box_pool_advisor_agent():
    assert isinstance(create_agent(), BoxPoolAdvisorAgent)

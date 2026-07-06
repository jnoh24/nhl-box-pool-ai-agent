"""MCP server exposing NHL box pool optimizer tools.

The plain Python tool functions are kept importable for tests and local use.
`create_server` wires those functions into the Python MCP SDK.
"""

from agent.preference_parser import parse_preferences
from tools.optimizer import optimize_lineup


def optimize_lineup_tool(preferences: dict[str, object]) -> dict[str, object]:
    """Return an optimized lineup for structured preferences."""
    return optimize_lineup(preferences)


def parse_preferences_tool(user_text: str) -> dict[str, object]:
    """Parse natural language preferences into optimizer preferences."""
    return parse_preferences(user_text)


def explain_tradeoffs_tool(preferences: dict[str, object]) -> dict[str, object]:
    """Return a concise explanation of optimizer tradeoffs."""
    result = optimize_lineup(preferences)
    return {
        "tradeoff_explanation": result["tradeoff_explanation"],
        "total_projected_points": result["total_projected_points"],
        "total_adjusted_score": result["total_adjusted_score"],
    }


def create_server():
    """Create and configure the MCP server."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Python MCP SDK is not installed. Install project dependencies with "
            "`python3 -m pip install -r requirements.txt`."
        ) from exc

    server = FastMCP("nhl-box-pool-agent")
    server.tool()(optimize_lineup_tool)
    server.tool()(parse_preferences_tool)
    server.tool()(explain_tradeoffs_tool)
    return server


def main() -> None:
    """Run the MCP server."""
    create_server().run()


if __name__ == "__main__":
    main()

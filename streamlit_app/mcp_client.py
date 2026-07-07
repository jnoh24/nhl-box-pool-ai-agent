"""Synchronous Streamlit helpers backed by the MCP stdio client."""

import asyncio
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MCPClientError(RuntimeError):
    """Raised when the local MCP client cannot call the MCP server."""


def call_parse_preferences(user_text: str) -> dict[str, object]:
    """Call the MCP parse preferences tool."""
    return _run_mcp_tool_sync("parse_preferences_tool", {"user_text": user_text})


def call_optimize_lineup(
    preferences: dict[str, object],
    pool_records: list[dict[str, object]] | None,
) -> dict[str, object]:
    """Call the MCP optimize lineup tool."""
    return _run_mcp_tool_sync(
        "optimize_lineup_tool",
        {
            "preferences": preferences,
            "pool_records": pool_records,
        },
    )


def call_explain_tradeoffs(
    preferences: dict[str, object],
    pool_records: list[dict[str, object]] | None,
) -> dict[str, object]:
    """Call the MCP explain tradeoffs tool."""
    return _run_mcp_tool_sync(
        "explain_tradeoffs_tool",
        {
            "preferences": preferences,
            "pool_records": pool_records,
        },
    )


def _run_mcp_tool_sync(tool_name: str, arguments: dict[str, object]) -> dict[str, object]:
    """Run an async MCP tool call from synchronous Streamlit code."""
    coroutine = _call_mcp_tool(tool_name, arguments)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)

    # Streamlit is normally synchronous, but this avoids event-loop conflicts if
    # a host environment already owns the current loop.
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(coroutine)).result()


async def _call_mcp_tool(tool_name: str, arguments: dict[str, object]) -> dict[str, object]:
    """Call a tool on the local MCP server over stdio."""
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ModuleNotFoundError as exc:
        raise MCPClientError(
            "Python MCP SDK is not installed. Install project dependencies with "
            "`python3 -m pip install -r requirements.txt` before using MCP mode."
        ) from exc

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(PROJECT_ROOT)
        if not existing_pythonpath
        else f"{PROJECT_ROOT}{os.pathsep}{existing_pythonpath}"
    )
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        env=env,
    )

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
    except Exception as exc:
        if isinstance(exc, MCPClientError):
            raise
        raise MCPClientError(f"MCP tool call failed for {tool_name}: {exc}") from exc

    return _decode_mcp_tool_result(result)


def _decode_mcp_tool_result(result: Any) -> dict[str, object]:
    """Convert an MCP CallToolResult into a normal Python dictionary."""
    structured_content = getattr(result, "structuredContent", None)
    if structured_content is None:
        structured_content = getattr(result, "structured_content", None)
    if isinstance(structured_content, dict):
        return structured_content

    content = getattr(result, "content", None)
    if not content:
        return {}

    first_item = content[0]
    text = getattr(first_item, "text", None)
    if text is None and isinstance(first_item, dict):
        text = first_item.get("text")
    if text is None:
        raise MCPClientError("MCP tool returned a response without text content.")

    try:
        decoded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MCPClientError(f"MCP tool returned invalid JSON: {text}") from exc
    if not isinstance(decoded, dict):
        raise MCPClientError("MCP tool returned JSON that was not an object.")
    return decoded

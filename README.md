# NHL Box Pool AI Assistant

NHL Box Pool AI Assistant helps users turn a box pool CSV into an optimized lineup recommendation. It combines a simple Streamlit UI, rule-based preference parsing, dataset validation, and explainable scoring.

The assistant can:

- read a user-uploaded box pool CSV
- validate and clean the dataset
- detect missing optimization information
- ask the user for additional data when needed
- optimize lineups using user preferences
- explain lineup tradeoffs

## Upload Format

The minimum required upload columns are:

```csv
box,name,team
```

These columns identify which players are available in each box. They are enough for the app to validate and preview a pool, but not enough for meaningful optimization.

Recommended columns:

```csv
box,name,team,position,projected_points,risk,injury_status,popularity,salary
```

## Optimization Data

`projected_points` is required for meaningful optimization. If it is missing, the assistant can still clean and preview the dataset, but it will not run lineup optimization.

`popularity` enables chalk and contrarian strategy choices:

- `chalk` rewards high-popularity players
- `contrarian` rewards lower-popularity players
- if `popularity` is missing, the app falls back to balanced strategy

`risk` enables safe and risky strategy modes:

- `safe` penalizes higher-risk players more heavily
- `risky` gives high-upside players more room
- if `risk` is missing, the app falls back to balanced risk mode

## Preferences

Users can combine natural language instructions with UI controls. Supported preferences include locked players, banned players, banned teams, preferred teams, risk mode, and strategy.

The optimizer selects exactly one player from each box, applies the user preferences, and returns total projected points, total adjusted score, and an explanation of the tradeoffs.

## Run The App

Install dependencies, including the Python MCP SDK:

```bash
python3 -m pip install -r requirements.txt
```

Start the Streamlit app:

```bash
streamlit run streamlit_app/app.py
```

If the MCP SDK is missing or the local MCP server cannot start, the app shows a clear error instead of silently bypassing MCP.

## MCP Architecture

The app uses true MCP protocol communication for optimization calls:

```text
Streamlit UI -> MCP client -> MCP stdio server -> agent tools -> parser/optimizer/scoring
```

`streamlit_app/app.py` calls helper functions in `streamlit_app/mcp_client.py`. Those helpers start the local MCP server with stdio transport using:

```bash
python -m mcp_server.server
```

Then the client calls these registered MCP tools by name:

- `parse_preferences_tool`
- `optimize_lineup_tool`
- `explain_tradeoffs_tool`

Uploaded CSV data is passed to MCP as `pool_records`, converted back into a dataframe inside the server tool, and then sent to the optimizer. If no uploaded data is provided, the optimizer falls back to `data/sample_pool.csv`.

The client currently opens a short-lived stdio MCP server session per tool call. That keeps Streamlit reruns simple and avoids stale subprocess or event-loop state. The public Streamlit-facing functions remain synchronous:

- `call_parse_preferences(user_text)`
- `call_optimize_lineup(preferences, pool_records)`
- `call_explain_tradeoffs(preferences, pool_records)`

## Run The MCP Server Manually

From the project root:

```bash
python3 -m mcp_server.server
```

The process uses stdio transport, so it will wait for an MCP client rather than serving a browser page. To confirm Streamlit is using MCP, run the app, optimize a lineup, and verify errors mention MCP if the SDK/server is unavailable. You can also inspect `streamlit_app/app.py`: it calls the MCP client helpers, not the parser or optimizer directly.

## Tests

Run the test suite:

```bash
python3 -m pytest
```

The lightweight MCP client tests mock the low-level SDK call so they do not require a long-running external MCP server. Server wrapper tests verify the tools accept uploaded `pool_records`.

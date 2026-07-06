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

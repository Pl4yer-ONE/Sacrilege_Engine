# MCP Integration

Sacrilege Engine exposes an MCP (Model Context Protocol) server for integration with AI assistants like Claude and GPT.

## Available Tools

| Tool | Description |
|:-----|:------------|
| `analyze_demo` | Full death analysis with blame scores |
| `get_player_rankings` | Player rankings (S-F grades) |
| `list_demos` | List available demo files |
| `get_death_details` | Detailed analysis for a specific player |
| `get_mistake_summary` | Summary of mistake types |

## Setup for Claude Desktop

1. Install the MCP dependency:
```bash
pip install mcp
```

2. Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "sacrilege-engine": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/Users/YOUR_USER/Sacrilege_Engine",
      "env": {
        "PYTHONPATH": "/Users/YOUR_USER/Sacrilege_Engine",
        "SACRILEGE_DEMO_DIR": "/Users/YOUR_USER/Sacrilege_Engine/demo files"
      }
    }
  }
}
```

3. Restart Claude Desktop

## Setup for GPT / Other Assistants

Run the MCP server directly:
```bash
cd /path/to/Sacrilege_Engine
PYTHONPATH=. python -m src.mcp_server
```

The server communicates over stdio using the MCP protocol.

## Example Usage (Claude)

Once configured, you can ask Claude:

- *"Analyze the demo boss-vs-m80-m2-ancient.dem"*
- *"Show me player rankings from the dust2 demo"*
- *"What were Snax's deaths like in gamerlegion-vs-venom-m2-dust2.dem?"*
- *"Give me a mistake summary for the mirage match"*

## Example Tool Response

```json
{
  "demo": "gamerlegion-vs-venom-m2-dust2.dem",
  "rankings": [
    {"rank": 1, "player": "REZ", "grade": "A", "score": 72.5, "kills": 24, "deaths": 15},
    {"rank": 2, "player": "Snax", "grade": "B", "score": 58.2, "kills": 18, "deaths": 17},
    ...
  ]
}
```

## Environment Variables

| Variable | Description | Default |
|:---------|:------------|:--------|
| `SACRILEGE_DEMO_DIR` | Directory containing .dem files | `./demo files` |

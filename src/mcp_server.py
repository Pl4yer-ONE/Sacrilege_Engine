#!/usr/bin/env python3
"""
Sacrilege Engine MCP Server
Model Context Protocol server for CS2 demo analysis.
Compatible with Claude, GPT 5.2, and other MCP-compatible AI assistants.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
)

# Initialize MCP server
server = Server("sacrilege-engine")

# Default demo directory
DEMO_DIR = Path(os.environ.get("SACRILEGE_DEMO_DIR", "./demo files"))


def get_demo_path(demo_name: str) -> Path:
    """Resolve demo path from name or full path."""
    if Path(demo_name).exists():
        return Path(demo_name)
    demo_path = DEMO_DIR / demo_name
    if demo_path.exists():
        return demo_path
    # Try adding .dem extension
    if not demo_name.endswith('.dem'):
        demo_path = DEMO_DIR / f"{demo_name}.dem"
        if demo_path.exists():
            return demo_path
    raise FileNotFoundError(f"Demo not found: {demo_name}")


def parse_demo(demo_path: Path) -> dict:
    """Parse demo file and return structured data."""
    from demoparser2 import DemoParser
    import pandas as pd
    
    parser = DemoParser(str(demo_path))
    
    # Get header info
    header = parser.parse_header()
    map_name = header.get('map_name', 'unknown')
    
    # Parse kills
    kills_df = parser.parse_event("player_death", other=["total_rounds_played"])
    
    # Parse player positions
    tick_fields = ["X", "Y", "Z", "health", "armor_value", "is_alive", "team_num"]
    tick_df = parser.parse_ticks(tick_fields)
    
    # Convert kills to list of dicts
    kills = []
    for _, row in kills_df.iterrows():
        kills.append({
            'tick': int(row.get('tick', 0)),
            'round': int(row.get('total_rounds_played', 0)) + 1,
            'attacker': row.get('attacker_name', ''),
            'attacker_steamid': row.get('attacker_steamid', ''),
            'attacker_team': 'CT' if row.get('attacker_steamid', '') in get_ct_steamids(tick_df, row.get('tick', 0)) else 'T',
            'victim': row.get('user_name', ''),
            'victim_steamid': row.get('user_steamid', ''),
            'weapon': row.get('weapon', ''),
            'headshot': bool(row.get('headshot', False)),
            'distance': float(row.get('distance', 0)),
        })
    
    return {
        'map': map_name,
        'kills': kills,
        'tick_df': tick_df,
    }


def get_ct_steamids(tick_df, tick: int) -> set:
    """Get CT team steamids at a specific tick."""
    try:
        data = tick_df[tick_df['tick'] == tick]
        ct_ids = set()
        for _, row in data.iterrows():
            if row.get('team_num', 0) == 3:  # CT team
                ct_ids.add(str(row.get('steamid', '')))
        return ct_ids
    except:
        return set()


def get_players_at_tick(tick_df, tick: int) -> list:
    """Get player data at a specific tick."""
    try:
        data = tick_df[tick_df['tick'] == tick]
        players = []
        for _, row in data.iterrows():
            team_num = row.get('team_num', 0)
            team = 'CT' if team_num == 3 else 'T' if team_num == 2 else 'SPEC'
            players.append({
                'steamid': str(row.get('steamid', '')),
                'name': row.get('name', ''),
                'team': team,
                'x': float(row.get('X', 0)),
                'y': float(row.get('Y', 0)),
                'z': float(row.get('Z', 0)),
                'health': int(row.get('health', 0)),
                'alive': bool(row.get('is_alive', False)),
            })
        return players
    except:
        return []


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools for AI assistants."""
    return [
        Tool(
            name="analyze_demo",
            description="Analyze a CS2 demo file and return death analysis with blame scores, mistake types, and performance grades.",
            inputSchema={
                "type": "object",
                "properties": {
                    "demo_path": {
                        "type": "string",
                        "description": "Path to the .dem file or demo name in the demo directory"
                    },
                    "max_rounds": {
                        "type": "integer",
                        "description": "Maximum number of rounds to analyze (default: all)",
                        "default": 0
                    }
                },
                "required": ["demo_path"]
            }
        ),
        Tool(
            name="get_player_rankings",
            description="Get player performance rankings (S-F grades) from a demo with blame scores and K/D ratios.",
            inputSchema={
                "type": "object",
                "properties": {
                    "demo_path": {
                        "type": "string",
                        "description": "Path to the .dem file"
                    }
                },
                "required": ["demo_path"]
            }
        ),
        Tool(
            name="list_demos",
            description="List available demo files in the configured demo directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Optional directory to list demos from",
                        "default": ""
                    }
                }
            }
        ),
        Tool(
            name="get_death_details",
            description="Get detailed analysis for a specific player's deaths in a demo.",
            inputSchema={
                "type": "object",
                "properties": {
                    "demo_path": {
                        "type": "string",
                        "description": "Path to the .dem file"
                    },
                    "player_name": {
                        "type": "string",
                        "description": "Player name to analyze"
                    }
                },
                "required": ["demo_path", "player_name"]
            }
        ),
        Tool(
            name="get_mistake_summary",
            description="Get a summary of mistake types across all deaths in a demo.",
            inputSchema={
                "type": "object",
                "properties": {
                    "demo_path": {
                        "type": "string",
                        "description": "Path to the .dem file"
                    }
                },
                "required": ["demo_path"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls from AI assistants."""
    
    if name == "list_demos":
        return await handle_list_demos(arguments)
    elif name == "analyze_demo":
        return await handle_analyze_demo(arguments)
    elif name == "get_player_rankings":
        return await handle_get_rankings(arguments)
    elif name == "get_death_details":
        return await handle_death_details(arguments)
    elif name == "get_mistake_summary":
        return await handle_mistake_summary(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def handle_list_demos(arguments: dict) -> list[TextContent]:
    """List available demo files."""
    directory = arguments.get("directory", "") or DEMO_DIR
    demo_dir = Path(directory)
    
    if not demo_dir.exists():
        return [TextContent(type="text", text=f"Directory not found: {demo_dir}")]
    
    demos = list(demo_dir.glob("*.dem"))
    
    if not demos:
        return [TextContent(type="text", text=f"No demo files found in {demo_dir}")]
    
    result = {
        "directory": str(demo_dir),
        "count": len(demos),
        "demos": [
            {
                "name": d.name,
                "size_mb": round(d.stat().st_size / (1024 * 1024), 1),
            }
            for d in sorted(demos)
        ]
    }
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_analyze_demo(arguments: dict) -> list[TextContent]:
    """Analyze a demo and return death analysis."""
    try:
        demo_path = get_demo_path(arguments["demo_path"])
        max_rounds = arguments.get("max_rounds", 0)
    except FileNotFoundError as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    try:
        from src.intelligence.death_analyzer import DeathAnalyzer
        
        # Parse demo
        demo_data = parse_demo(demo_path)
        
        # Initialize analyzer
        analyzer = DeathAnalyzer()
        
        # Process kills
        deaths_analyzed = []
        for kill in demo_data['kills']:
            if max_rounds > 0 and kill['round'] > max_rounds:
                break
            
            # Get players at kill tick
            tick = kill['tick']
            players = get_players_at_tick(demo_data['tick_df'], tick)
            
            # Build kill dict for analyzer
            kill_data = {
                'attacker': kill['attacker'],
                'attacker_team': kill['attacker_team'],
                'victim': kill['victim'],
                'victim_team': 'CT' if kill['attacker_team'] == 'T' else 'T',
                'victim_id': kill['victim_steamid'],
                'weapon': kill['weapon'],
                'hs': kill['headshot'],
            }
            
            # Get victim position
            for p in players:
                if p['name'] == kill['victim']:
                    kill_data['victim_pos'] = type('Pos', (), {'x': p['x'], 'y': p['y']})()
                    break
            
            # Analyze death
            analysis = analyzer.analyze_death(
                kill_data, players, [], [], [], [], tick, kill['round']
            )
            
            deaths_analyzed.append({
                "round": kill['round'],
                "victim": analysis.victim_name,
                "attacker": analysis.attacker_name,
                "weapon": kill['weapon'],
                "headshot": kill['headshot'],
                "primary_mistake": analysis.primary_mistake().value,
                "all_mistakes": [m.value for m in analysis.mistakes],
                "blame_score": round(analysis.blame_score(), 1),
                "severity": analysis.severity,
                "teammate_distance": round(analysis.teammate_distance, 0),
                "enemy_count": analysis.enemy_count,
                "was_traded": analysis.was_traded,
            })
        
        result = {
            "demo": demo_path.name,
            "map": demo_data['map'],
            "total_deaths": len(deaths_analyzed),
            "deaths": deaths_analyzed[:50]  # Limit to 50 for response size
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": f"Analysis error: {str(e)}"}))]


async def handle_get_rankings(arguments: dict) -> list[TextContent]:
    """Get player rankings from a demo."""
    try:
        demo_path = get_demo_path(arguments["demo_path"])
    except FileNotFoundError as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    try:
        from src.intelligence.death_analyzer import DeathAnalyzer
        
        demo_data = parse_demo(demo_path)
        analyzer = DeathAnalyzer()
        
        # Process all kills
        for kill in demo_data['kills']:
            tick = kill['tick']
            players = get_players_at_tick(demo_data['tick_df'], tick)
            
            kill_data = {
                'attacker': kill['attacker'],
                'attacker_team': kill['attacker_team'],
                'victim': kill['victim'],
                'victim_team': 'CT' if kill['attacker_team'] == 'T' else 'T',
                'victim_id': kill['victim_steamid'],
                'weapon': kill['weapon'],
                'hs': kill['headshot'],
            }
            
            for p in players:
                if p['name'] == kill['victim']:
                    kill_data['victim_pos'] = type('Pos', (), {'x': p['x'], 'y': p['y']})()
                    break
            
            analyzer.analyze_death(kill_data, players, [], [], [], [], tick, kill['round'])
            analyzer.update_kill(kill['attacker'], kill['attacker_team'])
        
        # Get rankings
        rankings = analyzer.get_rankings()
        
        result = {
            "demo": demo_path.name,
            "map": demo_data['map'],
            "rankings": [
                {
                    "rank": i + 1,
                    "player": r.name,
                    "team": r.team,
                    "grade": r.rank_grade,
                    "score": round(r.performance_score, 1),
                    "kills": r.kills,
                    "deaths": r.deaths,
                    "avg_blame": round(r.avg_blame, 1) if r.deaths > 0 else 0
                }
                for i, r in enumerate(rankings)
            ]
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": f"Rankings error: {str(e)}"}))]


async def handle_death_details(arguments: dict) -> list[TextContent]:
    """Get detailed death analysis for a specific player."""
    try:
        demo_path = get_demo_path(arguments["demo_path"])
        player_name = arguments["player_name"].lower()
    except (FileNotFoundError, KeyError) as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    try:
        from src.intelligence.death_analyzer import DeathAnalyzer
        
        demo_data = parse_demo(demo_path)
        analyzer = DeathAnalyzer()
        player_deaths = []
        
        for kill in demo_data['kills']:
            if kill['victim'].lower() != player_name:
                continue
            
            tick = kill['tick']
            players = get_players_at_tick(demo_data['tick_df'], tick)
            
            kill_data = {
                'attacker': kill['attacker'],
                'attacker_team': kill['attacker_team'],
                'victim': kill['victim'],
                'victim_team': 'CT' if kill['attacker_team'] == 'T' else 'T',
                'victim_id': kill['victim_steamid'],
                'weapon': kill['weapon'],
                'hs': kill['headshot'],
            }
            
            for p in players:
                if p['name'] == kill['victim']:
                    kill_data['victim_pos'] = type('Pos', (), {'x': p['x'], 'y': p['y']})()
                    break
            
            analysis = analyzer.analyze_death(kill_data, players, [], [], [], [], tick, kill['round'])
            
            player_deaths.append({
                "round": kill['round'],
                "killed_by": analysis.attacker_name,
                "weapon": kill['weapon'],
                "headshot": kill['headshot'],
                "primary_mistake": analysis.primary_mistake().value,
                "all_mistakes": [m.value for m in analysis.mistakes],
                "blame_score": round(analysis.blame_score(), 1),
                "teammate_distance": round(analysis.teammate_distance, 0),
                "was_traded": analysis.was_traded
            })
        
        if not player_deaths:
            return [TextContent(type="text", text=json.dumps({
                "error": f"No deaths found for player: {player_name}",
                "suggestion": "Check player name spelling (case-insensitive)"
            }))]
        
        avg_blame = sum(d['blame_score'] for d in player_deaths) / len(player_deaths)
        
        result = {
            "player": arguments["player_name"],
            "demo": demo_path.name,
            "total_deaths": len(player_deaths),
            "average_blame": round(avg_blame, 1),
            "deaths": player_deaths
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": f"Death details error: {str(e)}"}))]


async def handle_mistake_summary(arguments: dict) -> list[TextContent]:
    """Get summary of mistake types across a demo."""
    try:
        demo_path = get_demo_path(arguments["demo_path"])
    except FileNotFoundError as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    try:
        from src.intelligence.death_analyzer import DeathAnalyzer
        
        demo_data = parse_demo(demo_path)
        analyzer = DeathAnalyzer()
        mistake_counts: dict[str, int] = {}
        total_deaths = 0
        
        for kill in demo_data['kills']:
            tick = kill['tick']
            players = get_players_at_tick(demo_data['tick_df'], tick)
            
            kill_data = {
                'attacker': kill['attacker'],
                'attacker_team': kill['attacker_team'],
                'victim': kill['victim'],
                'victim_team': 'CT' if kill['attacker_team'] == 'T' else 'T',
                'victim_id': kill['victim_steamid'],
                'weapon': kill['weapon'],
                'hs': kill['headshot'],
            }
            
            for p in players:
                if p['name'] == kill['victim']:
                    kill_data['victim_pos'] = type('Pos', (), {'x': p['x'], 'y': p['y']})()
                    break
            
            analysis = analyzer.analyze_death(kill_data, players, [], [], [], [], tick, kill['round'])
            
            total_deaths += 1
            for mistake in analysis.mistakes:
                mistake_counts[mistake.value] = mistake_counts.get(mistake.value, 0) + 1
        
        # Sort by count
        sorted_mistakes = sorted(mistake_counts.items(), key=lambda x: -x[1])
        
        result = {
            "demo": demo_path.name,
            "map": demo_data['map'],
            "total_deaths": total_deaths,
            "mistake_distribution": [
                {
                    "type": m,
                    "count": c,
                    "percentage": round(c / total_deaths * 100, 1) if total_deaths > 0 else 0
                }
                for m, c in sorted_mistakes
            ]
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": f"Mistake summary error: {str(e)}"}))]


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List demo files as resources."""
    resources = []
    
    if DEMO_DIR.exists():
        for demo in DEMO_DIR.glob("*.dem"):
            resources.append(Resource(
                uri=f"demo://{demo.name}",
                name=demo.name,
                description=f"CS2 demo file ({demo.stat().st_size // (1024*1024)}MB)",
                mimeType="application/octet-stream"
            ))
    
    return resources


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

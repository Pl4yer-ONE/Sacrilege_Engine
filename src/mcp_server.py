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
    ResourceTemplate,
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
                "path": str(d)
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
        return [TextContent(type="text", text=str(e))]
    
    # Import here to avoid loading unless needed
    from src.parser.demo_parser import DemoParser
    from src.intelligence.death_analyzer import DeathAnalyzer
    
    try:
        # Parse demo
        parser = DemoParser()
        demo_data = parser.parse(str(demo_path))
        
        # Initialize analyzer
        analyzer = DeathAnalyzer()
        
        # Process all kills
        deaths_analyzed = []
        for kill in demo_data.get('kills', []):
            # Get players at kill tick
            tick = kill.get('tick', 0)
            players = demo_data.get('players_at_tick', {}).get(tick, [])
            
            analysis = analyzer.analyze_death(
                kill, players, 
                demo_data.get('smokes', []),
                demo_data.get('mollies', []),
                demo_data.get('flashes', []),
                [], tick, kill.get('round', 1)
            )
            
            deaths_analyzed.append({
                "victim": analysis.victim_name,
                "attacker": analysis.attacker_name,
                "round": kill.get('round', 0),
                "primary_mistake": analysis.primary_mistake().value,
                "all_mistakes": [m.value for m in analysis.mistakes],
                "blame_score": round(analysis.blame_score(), 1),
                "severity": analysis.severity,
                "teammate_distance": round(analysis.teammate_distance, 0),
                "enemy_count": analysis.enemy_count,
                "was_traded": analysis.was_traded,
                "reasons": analysis.reasons
            })
            
            if max_rounds > 0 and kill.get('round', 0) > max_rounds:
                break
        
        result = {
            "demo": demo_path.name,
            "map": demo_data.get('map', 'unknown'),
            "total_deaths": len(deaths_analyzed),
            "deaths": deaths_analyzed
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except Exception as e:
        return [TextContent(type="text", text=f"Analysis error: {str(e)}")]


async def handle_get_rankings(arguments: dict) -> list[TextContent]:
    """Get player rankings from a demo."""
    try:
        demo_path = get_demo_path(arguments["demo_path"])
    except FileNotFoundError as e:
        return [TextContent(type="text", text=str(e))]
    
    from src.parser.demo_parser import DemoParser
    from src.intelligence.death_analyzer import DeathAnalyzer
    
    try:
        parser = DemoParser()
        demo_data = parser.parse(str(demo_path))
        
        analyzer = DeathAnalyzer()
        
        # Process all kills to build stats
        for kill in demo_data.get('kills', []):
            tick = kill.get('tick', 0)
            players = demo_data.get('players_at_tick', {}).get(tick, [])
            
            analyzer.analyze_death(
                kill, players,
                demo_data.get('smokes', []),
                demo_data.get('mollies', []),
                demo_data.get('flashes', []),
                [], tick, kill.get('round', 1)
            )
            analyzer.update_kill(kill.get('attacker', ''), kill.get('attacker_team', 'T'))
        
        # Get rankings
        rankings = analyzer.get_rankings()
        
        result = {
            "demo": demo_path.name,
            "rankings": [
                {
                    "rank": i + 1,
                    "player": r.name,
                    "team": r.team,
                    "grade": r.grade,
                    "score": round(r.performance_score(), 1),
                    "kills": r.kills,
                    "deaths": r.deaths,
                    "avg_blame": round(r.avg_blame(), 1)
                }
                for i, r in enumerate(rankings)
            ]
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except Exception as e:
        return [TextContent(type="text", text=f"Rankings error: {str(e)}")]


async def handle_death_details(arguments: dict) -> list[TextContent]:
    """Get detailed death analysis for a specific player."""
    try:
        demo_path = get_demo_path(arguments["demo_path"])
        player_name = arguments["player_name"]
    except (FileNotFoundError, KeyError) as e:
        return [TextContent(type="text", text=str(e))]
    
    from src.parser.demo_parser import DemoParser
    from src.intelligence.death_analyzer import DeathAnalyzer
    
    try:
        parser = DemoParser()
        demo_data = parser.parse(str(demo_path))
        
        analyzer = DeathAnalyzer()
        player_deaths = []
        
        for kill in demo_data.get('kills', []):
            if kill.get('victim', '').lower() != player_name.lower():
                continue
                
            tick = kill.get('tick', 0)
            players = demo_data.get('players_at_tick', {}).get(tick, [])
            
            analysis = analyzer.analyze_death(
                kill, players,
                demo_data.get('smokes', []),
                demo_data.get('mollies', []),
                demo_data.get('flashes', []),
                [], tick, kill.get('round', 1)
            )
            
            player_deaths.append({
                "round": kill.get('round', 0),
                "killed_by": analysis.attacker_name,
                "weapon": kill.get('weapon', 'unknown'),
                "primary_mistake": analysis.primary_mistake().value,
                "all_mistakes": [m.value for m in analysis.mistakes],
                "blame_score": round(analysis.blame_score(), 1),
                "reasons": analysis.reasons,
                "teammate_distance": round(analysis.teammate_distance, 0),
                "was_traded": analysis.was_traded
            })
        
        if not player_deaths:
            return [TextContent(type="text", text=f"No deaths found for player: {player_name}")]
        
        avg_blame = sum(d['blame_score'] for d in player_deaths) / len(player_deaths)
        
        result = {
            "player": player_name,
            "total_deaths": len(player_deaths),
            "average_blame": round(avg_blame, 1),
            "deaths": player_deaths
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except Exception as e:
        return [TextContent(type="text", text=f"Death details error: {str(e)}")]


async def handle_mistake_summary(arguments: dict) -> list[TextContent]:
    """Get summary of mistake types across a demo."""
    try:
        demo_path = get_demo_path(arguments["demo_path"])
    except FileNotFoundError as e:
        return [TextContent(type="text", text=str(e))]
    
    from src.parser.demo_parser import DemoParser
    from src.intelligence.death_analyzer import DeathAnalyzer, MistakeType
    
    try:
        parser = DemoParser()
        demo_data = parser.parse(str(demo_path))
        
        analyzer = DeathAnalyzer()
        mistake_counts: dict[str, int] = {}
        total_deaths = 0
        
        for kill in demo_data.get('kills', []):
            tick = kill.get('tick', 0)
            players = demo_data.get('players_at_tick', {}).get(tick, [])
            
            analysis = analyzer.analyze_death(
                kill, players,
                demo_data.get('smokes', []),
                demo_data.get('mollies', []),
                demo_data.get('flashes', []),
                [], tick, kill.get('round', 1)
            )
            
            total_deaths += 1
            for mistake in analysis.mistakes:
                mistake_counts[mistake.value] = mistake_counts.get(mistake.value, 0) + 1
        
        # Sort by count
        sorted_mistakes = sorted(mistake_counts.items(), key=lambda x: -x[1])
        
        result = {
            "demo": demo_path.name,
            "total_deaths": total_deaths,
            "mistake_distribution": [
                {
                    "type": m,
                    "count": c,
                    "percentage": round(c / total_deaths * 100, 1)
                }
                for m, c in sorted_mistakes
            ]
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except Exception as e:
        return [TextContent(type="text", text=f"Mistake summary error: {str(e)}")]


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

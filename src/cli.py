"""CLI entry point for Sacrilege Engine."""

import argparse
import sys
from pathlib import Path

from src.analysis_orchestrator import AnalysisOrchestrator
from src.output.feedback_generator import FeedbackGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Sacrilege Engine - CS2 Demo Decision Intelligence"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a demo file")
    analyze_parser.add_argument("demo", type=Path, help="Path to .dem file")
    analyze_parser.add_argument(
        "--player", "-p",
        type=str,
        help="Steam ID of player to analyze (default: all)"
    )
    analyze_parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format"
    )
    
    # Server command
    server_parser = subparsers.add_parser("server", help="Start API server")
    server_parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to"
    )
    server_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to"
    )
    
    args = parser.parse_args()
    
    if args.command == "analyze":
        run_analyze(args)
    elif args.command == "server":
        run_server(args)
    else:
        parser.print_help()


def run_analyze(args):
    """Run demo analysis."""
    demo_path = args.demo
    
    if not demo_path.exists():
        print(f"Error: File not found: {demo_path}")
        sys.exit(1)
    
    if not demo_path.suffix == '.dem':
        print("Error: File must be a .dem file")
        sys.exit(1)
    
    print(f"Analyzing: {demo_path}")
    print("-" * 40)
    
    orchestrator = AnalysisOrchestrator()
    result = orchestrator.analyze(demo_path, target_player=args.player)
    
    if not result.success:
        print(f"Error: {result.error}")
        sys.exit(1)
    
    print(f"Map: {result.map_name}")
    print(f"Players analyzed: {len(result.player_reports)}")
    print()
    
    generator = FeedbackGenerator()
    
    for player_id, report in result.player_reports.items():
        if args.output == "json":
            import json
            print(json.dumps(generator.format_report_json(report), indent=2))
        else:
            print(generator.format_report_text(report))
        print()


def run_server(args):
    """Run API server."""
    import uvicorn
    from src.api.main import app
    
    print(f"Starting Sacrilege Engine API on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

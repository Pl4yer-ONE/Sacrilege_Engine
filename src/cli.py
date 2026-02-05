# SPDX-FileCopyrightText: 2026 Pl4yer-ONE <mahadevan.rajeev27@gmail.com>
# SPDX-License-Identifier: LicenseRef-Sacrilege-EULA

"""
Sacrilege Engine CLI - CS2 Demo Analysis Tool

Features:
- Single demo analysis
- Batch demo analysis (multiple demos)
- Player comparison mode
- Progress bar visualization
"""

import argparse
import sys
import json
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from src.analysis_orchestrator import AnalysisOrchestrator, FullAnalysisResult
from src.output.feedback_generator import FeedbackGenerator, AnalysisReport


# ============================================================================
# PROGRESS BAR
# ============================================================================

class ProgressBar:
    """Simple CLI progress bar with percentage and status."""
    
    def __init__(self, total: int, width: int = 40, prefix: str = ""):
        self.total = total
        self.width = width
        self.prefix = prefix
        self.current = 0
        self.status = ""
    
    def update(self, current: int, status: str = ""):
        """Update progress bar."""
        self.current = current
        self.status = status
        self._render()
    
    def increment(self, status: str = ""):
        """Increment by 1."""
        self.current += 1
        self.status = status
        self._render()
    
    def _render(self):
        """Render the progress bar to stdout."""
        if self.total == 0:
            percent = 100
        else:
            percent = (self.current / self.total) * 100
        
        filled = int(self.width * self.current // max(self.total, 1))
        bar = "█" * filled + "░" * (self.width - filled)
        
        status_display = f" {self.status[:30]}" if self.status else ""
        line = f"\r{self.prefix}[{bar}] {percent:5.1f}%{status_display}"
        
        sys.stdout.write(line.ljust(100))
        sys.stdout.flush()
    
    def complete(self, message: str = "Done!"):
        """Mark as complete."""
        self.current = self.total
        self.status = message
        self._render()
        print()  # New line


# ============================================================================
# BATCH ANALYSIS
# ============================================================================

@dataclass
class BatchResult:
    """Result from batch analysis."""
    path: Path
    success: bool
    result: Optional[FullAnalysisResult] = None
    error: Optional[str] = None
    duration: float = 0.0


def batch_analyze(demo_paths: list[Path], target_player: Optional[str] = None) -> list[BatchResult]:
    """
    Analyze multiple demo files with progress tracking.
    
    Args:
        demo_paths: List of paths to .dem files
        target_player: Optional steam_id to focus analysis on
    
    Returns:
        List of BatchResult for each demo
    """
    orchestrator = AnalysisOrchestrator()
    results: list[BatchResult] = []
    
    progress = ProgressBar(
        total=len(demo_paths),
        prefix="Analyzing: "
    )
    
    for i, path in enumerate(demo_paths):
        progress.update(i, f"{path.name}")
        
        start_time = time.time()
        
        try:
            result = orchestrator.analyze(path, target_player)
            duration = time.time() - start_time
            
            results.append(BatchResult(
                path=path,
                success=result.success,
                result=result,
                error=result.error,
                duration=duration
            ))
        except Exception as e:
            duration = time.time() - start_time
            results.append(BatchResult(
                path=path,
                success=False,
                error=str(e),
                duration=duration
            ))
    
    progress.complete(f"Completed {len(demo_paths)} demos")
    
    return results


def print_batch_summary(results: list[BatchResult]):
    """Print summary of batch analysis."""
    print("\n" + "=" * 60)
    print("BATCH ANALYSIS SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count
    total_time = sum(r.duration for r in results)
    
    print(f"\n✓ Successful: {success_count}")
    print(f"✗ Failed:     {fail_count}")
    print(f"⏱ Total time: {total_time:.1f}s")
    print(f"⏱ Avg time:   {total_time/max(len(results),1):.1f}s per demo")
    
    if fail_count > 0:
        print("\nFailed demos:")
        for r in results:
            if not r.success:
                print(f"  - {r.path.name}: {r.error}")
    
    print()


# ============================================================================
# PLAYER COMPARISON
# ============================================================================

def compare_players(
    result: FullAnalysisResult,
    player1_id: str,
    player2_id: str,
    feedback_gen: FeedbackGenerator
) -> None:
    """
    Compare two players from the same demo side-by-side.
    
    Args:
        result: Analysis result containing player reports
        player1_id: Steam ID of first player
        player2_id: Steam ID of second player
        feedback_gen: FeedbackGenerator instance
    """
    if not result.player_reports:
        print("Error: No player reports available")
        return
    
    # Get reports
    report1 = result.player_reports.get(player1_id)
    report2 = result.player_reports.get(player2_id)
    
    if not report1:
        print(f"Error: Player {player1_id} not found in analysis")
        return
    if not report2:
        print(f"Error: Player {player2_id} not found in analysis")
        return
    
    # Print comparison header
    print("\n" + "=" * 80)
    print("PLAYER COMPARISON")
    print("=" * 80)
    
    name1 = report1.player_name.center(35)
    name2 = report2.player_name.center(35)
    print(f"\n{name1} │ {name2}")
    print("─" * 35 + "┼" + "─" * 35)
    
    # Compare scores
    print("\n📊 MODULE SCORES:")
    print("─" * 72)
    
    all_modules = set(report1.scores.keys()) | set(report2.scores.keys())
    
    for module in sorted(all_modules):
        s1 = report1.scores.get(module, 0)
        s2 = report2.scores.get(module, 0)
        
        # Determine who's better
        if s1 > s2:
            indicator = "◀"
        elif s2 > s1:
            indicator = "▶"
        else:
            indicator = "="
        
        bar1 = _score_bar(s1, 15)
        bar2 = _score_bar(s2, 15)
        
        module_display = module[:20].ljust(20)
        print(f"  {module_display} {bar1} {s1:5.0f} │ {s2:5.0f} {bar2} {indicator}")
    
    # Calculate overall averages
    avg1 = sum(report1.scores.values()) / max(len(report1.scores), 1)
    avg2 = sum(report2.scores.values()) / max(len(report2.scores), 1)
    
    print("─" * 72)
    print(f"  {'OVERALL AVERAGE'.ljust(20)} {_score_bar(avg1, 15)} {avg1:5.0f} │ {avg2:5.0f} {_score_bar(avg2, 15)}")
    
    # Compare top mistakes
    print("\n\n🚨 TOP MISTAKES:")
    print("─" * 72)
    
    print(f"\n  {report1.player_name}:")
    for i, m in enumerate(report1.top_mistakes[:3], 1):
        print(f"    {i}. {m.title}")
    
    print(f"\n  {report2.player_name}:")
    for i, m in enumerate(report2.top_mistakes[:3], 1):
        print(f"    {i}. {m.title}")
    
    # Compare fixes
    print("\n\n💡 RECOMMENDED FIXES:")
    print("─" * 72)
    
    print(f"\n  {report1.player_name}:")
    if report1.mechanical_fix:
        print(f"    🎯 {report1.mechanical_fix}")
    if report1.tactical_fix:
        print(f"    🧠 {report1.tactical_fix}")
    if report1.mental_fix:
        print(f"    💭 {report1.mental_fix}")
    
    print(f"\n  {report2.player_name}:")
    if report2.mechanical_fix:
        print(f"    🎯 {report2.mechanical_fix}")
    if report2.tactical_fix:
        print(f"    🧠 {report2.tactical_fix}")
    if report2.mental_fix:
        print(f"    💭 {report2.mental_fix}")
    
    # Winner declaration
    print("\n" + "=" * 72)
    if avg1 > avg2:
        diff = avg1 - avg2
        print(f"📈 {report1.player_name} performed better by {diff:.1f} points overall")
    elif avg2 > avg1:
        diff = avg2 - avg1
        print(f"📈 {report2.player_name} performed better by {diff:.1f} points overall")
    else:
        print("📊 Both players performed equally")
    print("=" * 72 + "\n")


def _score_bar(score: float, width: int) -> str:
    """Generate a mini score bar."""
    filled = int((score / 100) * width)
    return "▓" * filled + "░" * (width - filled)


def list_players(result: FullAnalysisResult) -> None:
    """Print list of players in the analysis."""
    if not result.player_reports:
        print("No players found in analysis")
        return
    
    print("\nPlayers in demo:")
    print("─" * 50)
    for pid, report in result.player_reports.items():
        print(f"  [{pid}] {report.player_name}")
    print()


# ============================================================================
# MAIN CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Sacrilege Engine - CS2 Demo Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single demo
  python -m src.cli analyze match.dem
  
  # Batch analyze multiple demos
  python -m src.cli batch *.dem
  python -m src.cli batch demo1.dem demo2.dem demo3.dem
  
  # Compare two players
  python -m src.cli compare match.dem --p1 STEAM_0:1:123 --p2 STEAM_0:1:456
  
  # List players in a demo
  python -m src.cli players match.dem
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a single demo")
    analyze_parser.add_argument("demo", type=Path, help="Path to .dem file")
    analyze_parser.add_argument("--player", "-p", help="Target player steam_id (optional)")
    analyze_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Analyze multiple demos")
    batch_parser.add_argument("demos", type=Path, nargs="+", help="Paths to .dem files")
    batch_parser.add_argument("--player", "-p", help="Target player steam_id (optional)")
    batch_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two players")
    compare_parser.add_argument("demo", type=Path, help="Path to .dem file")
    compare_parser.add_argument("--p1", required=True, help="First player steam_id")
    compare_parser.add_argument("--p2", required=True, help="Second player steam_id")
    
    # Players command
    players_parser = subparsers.add_parser("players", help="List players in demo")
    players_parser.add_argument("demo", type=Path, help="Path to .dem file")
    
    # API command
    api_parser = subparsers.add_parser("api", help="Start API server")
    api_parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    api_parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize
    orchestrator = AnalysisOrchestrator()
    feedback_gen = FeedbackGenerator()
    
    # Handle commands
    if args.command == "analyze":
        if not args.demo.exists():
            print(f"Error: File not found: {args.demo}")
            sys.exit(1)
        
        print(f"\n🎮 Analyzing: {args.demo.name}\n")
        
        progress = ProgressBar(total=100, prefix="Progress: ")
        
        progress.update(10, "Parsing demo...")
        result = orchestrator.analyze(args.demo, args.player)
        progress.update(80, "Generating report...")
        
        if not result.success:
            progress.complete("Failed!")
            print(f"\nError: {result.error}")
            sys.exit(1)
        
        progress.complete("Analysis complete!")
        
        # Output results
        if args.json:
            output = {
                "map": result.map_name,
                "players": {}
            }
            for pid, report in result.player_reports.items():
                output["players"][pid] = feedback_gen.format_report_json(report)
            print(json.dumps(output, indent=2))
        else:
            for report in result.player_reports.values():
                print(feedback_gen.format_report_text(report))
                print()
    
    elif args.command == "batch":
        # Validate all files exist
        valid_demos = []
        for demo in args.demos:
            if demo.exists():
                valid_demos.append(demo)
            else:
                print(f"Warning: File not found: {demo}")
        
        if not valid_demos:
            print("Error: No valid demo files found")
            sys.exit(1)
        
        print(f"\n🎮 Batch analyzing {len(valid_demos)} demos\n")
        
        results = batch_analyze(valid_demos, args.player)
        print_batch_summary(results)
        
        if args.json:
            output = []
            for br in results:
                demo_output = {
                    "file": str(br.path),
                    "success": br.success,
                    "duration": br.duration,
                    "error": br.error,
                }
                if br.success and br.result and br.result.player_reports:
                    demo_output["players"] = {
                        pid: feedback_gen.format_report_json(report)
                        for pid, report in br.result.player_reports.items()
                    }
                output.append(demo_output)
            print(json.dumps(output, indent=2))
        else:
            # Print individual reports
            for br in results:
                if br.success and br.result:
                    print(f"\n{'='*60}")
                    print(f"DEMO: {br.path.name}")
                    print(f"{'='*60}")
                    for report in br.result.player_reports.values():
                        print(feedback_gen.format_report_text(report))
    
    elif args.command == "compare":
        if not args.demo.exists():
            print(f"Error: File not found: {args.demo}")
            sys.exit(1)
        
        print(f"\n🎮 Analyzing for comparison: {args.demo.name}\n")
        
        progress = ProgressBar(total=100, prefix="Progress: ")
        progress.update(10, "Parsing demo...")
        
        result = orchestrator.analyze(args.demo)
        
        progress.update(90, "Comparing players...")
        
        if not result.success:
            progress.complete("Failed!")
            print(f"\nError: {result.error}")
            sys.exit(1)
        
        progress.complete("Ready!")
        
        compare_players(result, args.p1, args.p2, feedback_gen)
    
    elif args.command == "players":
        if not args.demo.exists():
            print(f"Error: File not found: {args.demo}")
            sys.exit(1)
        
        result = orchestrator.analyze(args.demo)
        
        if not result.success:
            print(f"Error: {result.error}")
            sys.exit(1)
        
        list_players(result)
    
    elif args.command == "api":
        import uvicorn
        from src.api.main import app
        
        print(f"\n🚀 Starting Sacrilege Engine API")
        print(f"   http://{args.host}:{args.port}")
        print(f"   Docs: http://{args.host}:{args.port}/docs\n")
        
        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

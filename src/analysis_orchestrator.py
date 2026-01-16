"""Analysis orchestrator that runs all intelligence modules."""

from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from src.parser.demo_parser import DemoParser, ParseResult
from src.intelligence.peek_iq import PeekIQModule
from src.intelligence.trade_discipline import TradeDisciplineModule
from src.intelligence.crosshair_discipline import CrosshairDisciplineModule
from src.intelligence.utility_intelligence import UtilityIntelligenceModule
from src.intelligence.rotation_iq import RotationIQModule
from src.intelligence.tilt_detector import TiltDetectorModule
from src.intelligence.cheat_patterns import CheatPatternModule
from src.intelligence.round_simulator import RoundSimulatorModule
from src.intelligence.base import ModuleResult
from src.output.feedback_generator import FeedbackGenerator, AnalysisReport
from src.models import DemoData


@dataclass
class FullAnalysisResult:
    """Complete analysis result for a demo."""
    success: bool
    error: Optional[str] = None
    
    demo_hash: Optional[str] = None
    map_name: Optional[str] = None
    
    # Per-player reports
    player_reports: dict[str, AnalysisReport] = None
    
    # Raw module results (for detailed view)
    module_results: dict[str, list[ModuleResult]] = None


class AnalysisOrchestrator:
    """
    Orchestrates full demo analysis.
    
    Pipeline:
    1. Parse demo
    2. Run all intelligence modules per player
    3. Generate feedback reports
    """
    
    def __init__(self):
        self.parser = DemoParser()
        self.feedback_generator = FeedbackGenerator()
        
        # Initialize all 8 modules
        self.modules = [
            PeekIQModule(),
            TradeDisciplineModule(),
            CrosshairDisciplineModule(),
            UtilityIntelligenceModule(),
            RotationIQModule(),
            TiltDetectorModule(),
            CheatPatternModule(),
            RoundSimulatorModule(),
        ]
    
    def analyze(self, demo_path: Path, target_player: Optional[str] = None) -> FullAnalysisResult:
        """
        Run full analysis on a demo.
        
        Args:
            demo_path: Path to .dem file
            target_player: Optional steam_id to focus on. If None, analyze all.
        """
        # Parse demo
        parse_result = self.parser.parse(demo_path)
        
        if not parse_result.success:
            return FullAnalysisResult(
                success=False,
                error=parse_result.error
            )
        
        demo_data = parse_result.data
        
        # Determine which players to analyze
        if target_player:
            player_ids = [target_player] if target_player in demo_data.players else []
        else:
            player_ids = list(demo_data.players.keys())
        
        if not player_ids:
            return FullAnalysisResult(
                success=False,
                error="No players found to analyze"
            )
        
        # Run analysis per player
        player_reports: dict[str, AnalysisReport] = {}
        all_module_results: dict[str, list[ModuleResult]] = {}
        
        for player_id in player_ids:
            player_info = demo_data.players[player_id]
            module_results = self._run_modules(demo_data, player_id)
            
            all_module_results[player_id] = module_results
            
            # Generate report
            report = self.feedback_generator.generate_report(
                player_id=player_id,
                player_name=player_info.name,
                module_results=module_results
            )
            
            player_reports[player_id] = report
        
        return FullAnalysisResult(
            success=True,
            demo_hash=parse_result.file_hash,
            map_name=demo_data.header.map_name,
            player_reports=player_reports,
            module_results=all_module_results,
        )
    
    def _run_modules(self, demo_data: DemoData, player_id: str) -> list[ModuleResult]:
        """Run all intelligence modules for a player."""
        results: list[ModuleResult] = []
        
        for module in self.modules:
            try:
                result = module.analyze(demo_data, player_id)
                results.append(result)
            except Exception as e:
                # Log error but continue with other modules
                print(f"Error in module {module.name}: {e}")
        
        return results
    
    def analyze_quick(self, demo_path: Path) -> tuple[Optional[str], Optional[str]]:
        """Quick analysis to get map and duration."""
        header, error = self.parser.parse_quick(demo_path)
        if error:
            return None, error
        return header.map_name, None

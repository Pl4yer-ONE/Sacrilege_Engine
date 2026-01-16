"""Feedback generator that prioritizes and formats output."""

from dataclasses import dataclass, field
from typing import Optional

from src.intelligence.base import Feedback, FeedbackCategory, FeedbackSeverity, ModuleResult


@dataclass
class AnalysisReport:
    """Complete analysis report for a player."""
    player_id: str
    player_name: str
    
    # Top 3 mistakes
    top_mistakes: list[Feedback] = field(default_factory=list)
    
    # Categorized fixes
    mechanical_fix: Optional[str] = None
    tactical_fix: Optional[str] = None
    mental_fix: Optional[str] = None
    
    # Module scores
    scores: dict[str, float] = field(default_factory=dict)
    
    # All feedbacks (for detailed view)
    all_feedbacks: list[Feedback] = field(default_factory=list)


class FeedbackGenerator:
    """
    Generates final actionable feedback from module results.
    
    Rules:
    - Top 3 mistakes only (no stat spam)
    - 1 mechanical fix
    - 1 tactical fix
    - 1 mental fix
    """
    
    def generate_report(
        self,
        player_id: str,
        player_name: str,
        module_results: list[ModuleResult]
    ) -> AnalysisReport:
        """Generate complete analysis report."""
        # Collect all feedbacks
        all_feedbacks: list[Feedback] = []
        scores: dict[str, float] = {}
        
        for result in module_results:
            all_feedbacks.extend(result.feedbacks)
            scores[result.module_name] = result.score.overall_score
        
        # Sort by priority (lower = more important)
        all_feedbacks.sort(key=lambda f: (f.priority, f.severity.value))
        
        # Get top 3 mistakes
        top_mistakes = all_feedbacks[:3]
        
        # Get best fix per category
        mechanical_fix = self._get_best_fix(all_feedbacks, FeedbackCategory.MECHANICAL)
        tactical_fix = self._get_best_fix(all_feedbacks, FeedbackCategory.TACTICAL)
        mental_fix = self._get_best_fix(all_feedbacks, FeedbackCategory.MENTAL)
        
        return AnalysisReport(
            player_id=player_id,
            player_name=player_name,
            top_mistakes=top_mistakes,
            mechanical_fix=mechanical_fix,
            tactical_fix=tactical_fix,
            mental_fix=mental_fix,
            scores=scores,
            all_feedbacks=all_feedbacks,
        )
    
    def _get_best_fix(
        self,
        feedbacks: list[Feedback],
        category: FeedbackCategory
    ) -> Optional[str]:
        """Get the most important fix for a category."""
        category_feedbacks = [f for f in feedbacks if f.category == category]
        
        if not category_feedbacks:
            return None
        
        # Return fix from highest priority feedback
        best = min(category_feedbacks, key=lambda f: f.priority)
        return best.fix
    
    def format_report_text(self, report: AnalysisReport) -> str:
        """Format report as plain text."""
        lines = [
            f"=== SACRILEGE ENGINE REPORT ===",
            f"Player: {report.player_name}",
            "",
            "TOP 3 MISTAKES:",
            "-" * 40,
        ]
        
        for i, mistake in enumerate(report.top_mistakes, 1):
            rounds_str = f"[R{',R'.join(str(r) for r in mistake.rounds)}]" if mistake.rounds else ""
            lines.extend([
                f"{i}. {mistake.title} {rounds_str}",
                f"   {mistake.description}",
                f"   → {mistake.fix}",
                "",
            ])
        
        lines.extend([
            "YOUR FIXES:",
            "-" * 40,
        ])
        
        if report.mechanical_fix:
            lines.append(f"🎯 MECHANICAL: {report.mechanical_fix}")
        if report.tactical_fix:
            lines.append(f"🧠 TACTICAL: {report.tactical_fix}")
        if report.mental_fix:
            lines.append(f"💭 MENTAL: {report.mental_fix}")
        
        lines.extend([
            "",
            "SCORES:",
            "-" * 40,
        ])
        
        for module, score in report.scores.items():
            lines.append(f"  {module}: {score:.0f}/100")
        
        return "\n".join(lines)
    
    def format_report_json(self, report: AnalysisReport) -> dict:
        """Format report as JSON-serializable dict."""
        return {
            "player_id": report.player_id,
            "player_name": report.player_name,
            "top_mistakes": [
                {
                    "title": m.title,
                    "description": m.description,
                    "fix": m.fix,
                    "rounds": m.rounds,
                    "category": m.category.value,
                    "severity": m.severity.value,
                }
                for m in report.top_mistakes
            ],
            "fixes": {
                "mechanical": report.mechanical_fix,
                "tactical": report.tactical_fix,
                "mental": report.mental_fix,
            },
            "scores": report.scores,
        }

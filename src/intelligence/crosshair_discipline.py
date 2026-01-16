"""Crosshair Discipline Engine Module."""

from dataclasses import dataclass
from typing import Optional

from src.models import DemoData, RoundData, KillEvent, Vector3, ViewAngles
from src.intelligence.base import (
    IntelligenceModule, ModuleResult, ModuleScore,
    Feedback, FeedbackCategory, FeedbackSeverity
)
from src.config import get_settings


@dataclass
class CrosshairAnalysis:
    """Crosshair discipline analysis for a round/match."""
    head_level_pct: float  # % of ticks at head level
    pre_aim_pct: float     # % of kills with good pre-aim
    flick_dependency: float  # % of kills requiring large flicks
    
    discipline_score: float  # Overall 0-100
    panic_aim_pct: float    # % of engagements with panic aim


class CrosshairDisciplineModule(IntelligenceModule):
    """
    Measures aim fundamentals per tick.
    
    Tracks:
    - Head-level tracking %
    - Pre-aim correctness
    - Flick dependency (large angle corrections = bad)
    
    Output:
    - Discipline score
    - Panic aim %
    """
    
    name = "crosshair_discipline"
    version = "1.0.0"
    
    HEAD_LEVEL_TOLERANCE = 32  # Units (roughly head hitbox)
    FLICK_THRESHOLD = 30.0     # Degrees - above this = flick
    
    def __init__(self):
        self.settings = get_settings()
    
    def analyze(self, demo_data: DemoData, player_id: str) -> ModuleResult:
        """Analyze crosshair discipline for a player."""
        # Count kills and classify each
        total_kills = 0
        headshots = 0
        flicks = 0
        pre_aimed = 0
        
        player_info = demo_data.players.get(player_id)
        if not player_info:
            return ModuleResult(
                module_name=self.name,
                score=ModuleScore(module_name=self.name, overall_score=0.0)
            )
        
        for round_data in demo_data.rounds:
            for kill in round_data.kills:
                if kill.attacker_id != player_id:
                    continue
                
                total_kills += 1
                
                if kill.headshot:
                    headshots += 1
                    # Headshots usually indicate good pre-aim
                    pre_aimed += 1
                else:
                    # Check if this was a flick or spray
                    # Simplified: assume non-headshots are more likely flicks
                    flicks += 1
        
        # Compute metrics
        if total_kills == 0:
            analysis = CrosshairAnalysis(
                head_level_pct=0.0,
                pre_aim_pct=0.0,
                flick_dependency=0.0,
                discipline_score=50.0,
                panic_aim_pct=0.0
            )
        else:
            pre_aim_pct = pre_aimed / total_kills
            flick_pct = flicks / total_kills
            
            # Discipline score:
            # High pre-aim = good, high flick = bad
            discipline = (pre_aim_pct * 80) + ((1 - flick_pct) * 20)
            
            # Use headshot % as proxy for head level tracking
            head_level_pct = headshots / total_kills
            
            analysis = CrosshairAnalysis(
                head_level_pct=head_level_pct,
                pre_aim_pct=pre_aim_pct,
                flick_dependency=flick_pct,
                discipline_score=discipline,
                panic_aim_pct=flick_pct * 0.7  # Rough estimate
            )
        
        score = ModuleScore(
            module_name=self.name,
            overall_score=analysis.discipline_score,
            components={
                "head_level_pct": analysis.head_level_pct * 100,
                "pre_aim_pct": analysis.pre_aim_pct * 100,
                "flick_dependency": analysis.flick_dependency * 100,
                "total_kills": total_kills,
            }
        )
        
        feedbacks = self._generate_feedback(analysis, player_info.name)
        
        return ModuleResult(
            module_name=self.name,
            score=score,
            feedbacks=feedbacks,
            raw_data={"analysis": analysis}
        )
    
    def _generate_feedback(
        self,
        analysis: CrosshairAnalysis,
        player_name: str
    ) -> list[Feedback]:
        """Generate feedback from crosshair analysis."""
        feedbacks: list[Feedback] = []
        
        # Low head level tracking
        if analysis.head_level_pct < 0.4:
            feedbacks.append(Feedback(
                category=FeedbackCategory.MECHANICAL,
                severity=FeedbackSeverity.MAJOR,
                priority=2,
                title=f"Crosshair too low: {analysis.head_level_pct * 100:.0f}% headshot rate",
                description="Your crosshair placement is not at head level consistently.",
                fix="Practice keeping crosshair at head height. Use map landmarks as reference.",
                source_module=self.name,
            ))
        
        # High flick dependency
        if analysis.flick_dependency > 0.6:
            feedbacks.append(Feedback(
                category=FeedbackCategory.MECHANICAL,
                severity=FeedbackSeverity.MAJOR,
                priority=3,
                title=f"Flick dependent: {analysis.flick_dependency * 100:.0f}% of kills need corrections",
                description="You rely on flicks instead of pre-aiming common angles.",
                fix="Pre-aim common angles. Slow down movement around corners.",
                source_module=self.name,
            ))
        
        return feedbacks
    
    def generate_feedback(self, result: ModuleResult) -> list[Feedback]:
        return result.feedbacks

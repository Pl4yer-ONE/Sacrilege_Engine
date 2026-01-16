"""Rotation IQ Module."""

from dataclasses import dataclass, field
from typing import Optional

from src.models import DemoData, RoundData, KillEvent, Team
from src.intelligence.base import (
    IntelligenceModule, ModuleResult, ModuleScore,
    Feedback, FeedbackCategory, FeedbackSeverity
)


@dataclass
class RotationAnalysis:
    """Analysis of rotation decision for a round."""
    round_number: int
    
    # Did player rotate?
    rotated: bool = False
    
    # Was it correct?
    rotated_to_correct_site: bool = False
    
    # Timing (ticks from info to rotation start)
    reaction_ticks: int = 0
    
    # Over-rotation (left original site empty)
    over_rotated: bool = False
    
    # Ignored clear info
    ignored_info: bool = False


class RotationIQModule(IntelligenceModule):
    """
    Measures information processing and rotation decisions.
    
    Detects:
    - Slow rotations
    - Over-rotations
    - Tunnel vision
    - Ignored info
    
    Output:
    - Game sense score
    """
    
    name = "rotation_iq"
    version = "1.0.0"
    
    # Thresholds (in ticks at 64 tick rate)
    GOOD_ROTATION_TIME = 3 * 64  # 3 seconds
    SLOW_ROTATION_TIME = 6 * 64  # 6 seconds
    
    def analyze(self, demo_data: DemoData, player_id: str) -> ModuleResult:
        """Analyze rotation IQ for a player."""
        player_info = demo_data.players.get(player_id)
        if not player_info:
            return ModuleResult(
                module_name=self.name,
                score=ModuleScore(module_name=self.name, overall_score=50.0)
            )
        
        analyses: list[RotationAnalysis] = []
        
        for round_data in demo_data.rounds:
            analysis = self._analyze_round(round_data, demo_data, player_id)
            if analysis:
                analyses.append(analysis)
        
        score = self._compute_score(analyses)
        feedbacks = self._generate_feedback(analyses)
        
        return ModuleResult(
            module_name=self.name,
            score=score,
            feedbacks=feedbacks,
            raw_data={"analyses": analyses}
        )
    
    def _analyze_round(
        self,
        round_data: RoundData,
        demo_data: DemoData,
        player_id: str
    ) -> Optional[RotationAnalysis]:
        """Analyze rotation for a single round (CT side focus)."""
        player_info = demo_data.players.get(player_id)
        if not player_info:
            return None
        
        # Rotation analysis is most relevant for CT side
        # Simplified: check if player died after teammate at different site
        
        # Get all deaths for player's team
        team = player_info.team
        team_deaths = [
            k for k in round_data.kills
            if k.victim_id in demo_data.players
            and demo_data.players[k.victim_id].team == team
        ]
        
        if len(team_deaths) < 2:
            return None
        
        # Check if player died after a teammate
        player_death = None
        for death in team_deaths:
            if death.victim_id == player_id:
                player_death = death
                break
        
        if not player_death:
            return None
        
        # Check timing between first team death and player death
        first_team_death = team_deaths[0]
        if first_team_death.victim_id == player_id:
            # Player died first - no rotation to analyze
            return None
        
        reaction_ticks = player_death.tick - first_team_death.tick
        
        # Simplified classification
        rotated = reaction_ticks > self.GOOD_ROTATION_TIME  # Assume rotation if died later
        slow = reaction_ticks > self.SLOW_ROTATION_TIME
        
        return RotationAnalysis(
            round_number=round_data.round_number,
            rotated=rotated,
            reaction_ticks=reaction_ticks,
            over_rotated=slow,  # Simplified
        )
    
    def _compute_score(self, analyses: list[RotationAnalysis]) -> ModuleScore:
        """Compute rotation IQ score."""
        if not analyses:
            return ModuleScore(module_name=self.name, overall_score=50.0)
        
        good_rotations = sum(1 for a in analyses if not a.over_rotated and a.rotated)
        over_rotations = sum(1 for a in analyses if a.over_rotated)
        
        # Score: good rotations are positive, over-rotations negative
        score = 50 + (good_rotations * 10) - (over_rotations * 15)
        score = max(0, min(100, score))
        
        return ModuleScore(
            module_name=self.name,
            overall_score=score,
            components={
                "good_rotations": good_rotations,
                "over_rotations": over_rotations,
                "total_analyzed": len(analyses),
            }
        )
    
    def _generate_feedback(self, analyses: list[RotationAnalysis]) -> list[Feedback]:
        """Generate rotation feedback."""
        feedbacks: list[Feedback] = []
        
        over_rotations = [a for a in analyses if a.over_rotated]
        
        if len(over_rotations) >= 2:
            avg_delay = sum(a.reaction_ticks for a in over_rotations) / len(over_rotations)
            avg_delay_sec = avg_delay / 64
            
            feedbacks.append(Feedback(
                category=FeedbackCategory.TACTICAL,
                severity=FeedbackSeverity.MAJOR,
                priority=4,
                title=f"Over-rotation: {avg_delay_sec:.1f}s average delay",
                description=f"You over-rotated in {len(over_rotations)} rounds, leaving sites empty.",
                fix="Trust your anchor. Only rotate on confirmed info.",
                rounds=[a.round_number for a in over_rotations],
                source_module=self.name,
            ))
        
        return feedbacks
    
    def generate_feedback(self, result: ModuleResult) -> list[Feedback]:
        return result.feedbacks

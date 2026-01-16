"""Peek IQ Engine Module."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from src.models import (
    DemoData, RoundData, KillEvent, ShotEvent, PlayerState,
    Team, PeekClassification, Vector3, ViewAngles
)
from src.intelligence.base import (
    IntelligenceModule, ModuleResult, ModuleScore,
    Feedback, FeedbackCategory, FeedbackSeverity
)
from src.config import get_settings


@dataclass
class PeekAnalysis:
    """Analysis of a single peek/engagement."""
    tick: int
    round_number: int
    player_id: str
    
    classification: PeekClassification
    
    # Scores (0-1)
    pre_aim_score: float = 0.0
    info_score: float = 0.0
    trade_score: float = 0.0
    timing_score: float = 0.0
    
    # Outcome
    resulted_in_kill: bool = False
    resulted_in_death: bool = False
    damage_dealt: int = 0
    damage_taken: int = 0
    
    # Context
    angle_offset: float = 0.0  # Degrees off from enemy
    had_info: bool = False
    trade_available: bool = False
    
    position: Optional[Vector3] = None
    target_position: Optional[Vector3] = None


class PeekIQModule(IntelligenceModule):
    """
    Classifies every peek/engagement for decision quality.
    
    Classifications:
    - SMART: Pre-aimed, info-based, trade available
    - INFO_BASED: Based on sound/visual info
    - FORCED: Necessary due to situation (bomb, time)
    - EGO: Unnecessary risk, no info
    - PANIC: Reactive, poor crosshair placement
    """
    
    name = "peek_iq"
    version = "1.0.0"
    
    def __init__(self):
        self.settings = get_settings()
        self.pre_aim_threshold = self.settings.pre_aim_angle_threshold
        self.trade_distance = self.settings.trade_max_distance
    
    def analyze(self, demo_data: DemoData, player_id: str) -> ModuleResult:
        """Analyze peek quality for a specific player."""
        analyses: list[PeekAnalysis] = []
        
        for round_data in demo_data.rounds:
            round_analyses = self._analyze_round(round_data, demo_data, player_id)
            analyses.extend(round_analyses)
        
        score = self._compute_score(analyses)
        feedbacks = self.generate_feedback_from_analyses(analyses)
        
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
    ) -> list[PeekAnalysis]:
        """Analyze peeks in a single round."""
        analyses: list[PeekAnalysis] = []
        
        player_info = demo_data.players.get(player_id)
        if not player_info:
            return []
        
        player_team = player_info.team
        
        # Analyze each kill/death involving this player as engagement
        for kill in round_data.kills:
            if kill.attacker_id == player_id:
                # Player got a kill
                analysis = self._analyze_offensive_peek(
                    kill, round_data, demo_data, player_id, player_team
                )
                analyses.append(analysis)
            
            elif kill.victim_id == player_id:
                # Player died
                analysis = self._analyze_defensive_peek(
                    kill, round_data, demo_data, player_id, player_team
                )
                analyses.append(analysis)
        
        return analyses
    
    def _analyze_offensive_peek(
        self,
        kill: KillEvent,
        round_data: RoundData,
        demo_data: DemoData,
        player_id: str,
        player_team: Team
    ) -> PeekAnalysis:
        """Analyze a peek that resulted in a kill."""
        # Simplified analysis - in full impl, would have tick-level data
        
        # Check crosshair placement (was it pre-aimed?)
        pre_aim_score = 0.8 if kill.headshot else 0.5
        
        # Check if info-based (simplified)
        info_score = 0.3  # Default low, would check sound cues
        
        # Check trade availability (simplified)
        trade_score = 0.5  # Would check teammate positions
        
        # Classify
        total = pre_aim_score + info_score + trade_score
        
        if total > 2.0:
            classification = PeekClassification.SMART
        elif info_score > 0.6:
            classification = PeekClassification.INFO_BASED
        elif total > 1.2:
            classification = PeekClassification.FORCED
        else:
            classification = PeekClassification.EGO
        
        return PeekAnalysis(
            tick=kill.tick,
            round_number=round_data.round_number,
            player_id=player_id,
            classification=classification,
            pre_aim_score=pre_aim_score,
            info_score=info_score,
            trade_score=trade_score,
            resulted_in_kill=True,
            position=kill.attacker_position,
            target_position=kill.victim_position,
        )
    
    def _analyze_defensive_peek(
        self,
        death: KillEvent,
        round_data: RoundData,
        demo_data: DemoData,
        player_id: str,
        player_team: Team
    ) -> PeekAnalysis:
        """Analyze a peek that resulted in death."""
        # Deaths are more likely to be bad peeks
        pre_aim_score = 0.3  # Died, so probably not pre-aimed well
        info_score = 0.2
        trade_score = 0.3
        
        # Most deaths from peeks are ego or panic
        total = pre_aim_score + info_score + trade_score
        
        if total < 0.8:
            classification = PeekClassification.PANIC
        elif trade_score < 0.3:
            classification = PeekClassification.EGO
        else:
            classification = PeekClassification.FORCED
        
        return PeekAnalysis(
            tick=death.tick,
            round_number=round_data.round_number,
            player_id=player_id,
            classification=classification,
            pre_aim_score=pre_aim_score,
            info_score=info_score,
            trade_score=trade_score,
            resulted_in_death=True,
            position=death.victim_position,
            target_position=death.attacker_position,
        )
    
    def _compute_score(self, analyses: list[PeekAnalysis]) -> ModuleScore:
        """Compute peek IQ score."""
        if not analyses:
            return ModuleScore(module_name=self.name, overall_score=100.0)
        
        # Score by classification
        scores = {
            PeekClassification.SMART: 100,
            PeekClassification.INFO_BASED: 80,
            PeekClassification.FORCED: 60,
            PeekClassification.EGO: 30,
            PeekClassification.PANIC: 10,
            PeekClassification.NEUTRAL: 50,
        }
        
        total = sum(scores[a.classification] for a in analyses)
        avg = total / len(analyses)
        
        # Count by type
        by_type = {}
        for a in analyses:
            by_type[a.classification.value] = by_type.get(a.classification.value, 0) + 1
        
        return ModuleScore(
            module_name=self.name,
            overall_score=avg,
            components=by_type
        )
    
    def generate_feedback(self, result: ModuleResult) -> list[Feedback]:
        return result.feedbacks
    
    def generate_feedback_from_analyses(
        self,
        analyses: list[PeekAnalysis]
    ) -> list[Feedback]:
        """Generate feedback from peek analyses."""
        feedbacks: list[Feedback] = []
        
        # Count ego peeks
        ego = [a for a in analyses if a.classification == PeekClassification.EGO]
        panic = [a for a in analyses if a.classification == PeekClassification.PANIC]
        
        if len(ego) >= 2:
            rounds = list(set(a.round_number for a in ego))
            deaths = sum(1 for a in ego if a.resulted_in_death)
            
            feedbacks.append(Feedback(
                category=FeedbackCategory.TACTICAL,
                severity=FeedbackSeverity.CRITICAL if deaths >= 2 else FeedbackSeverity.MAJOR,
                priority=1,
                title=f"Ego peeks: {len(ego)} dry peeks without info",
                description=f"You took {len(ego)} unnecessary peeks. {deaths} resulted in death.",
                fix="Wait for utility or info before peeking. Check if trade is available.",
                rounds=rounds,
                source_module=self.name,
            ))
        
        if len(panic) >= 2:
            rounds = list(set(a.round_number for a in panic))
            
            feedbacks.append(Feedback(
                category=FeedbackCategory.MENTAL,
                severity=FeedbackSeverity.MAJOR,
                priority=3,
                title=f"Panic aim: {len(panic)} reactive engagements",
                description="You reacted poorly in engagements - crosshair misplacement.",
                fix="Pre-aim common angles. Don't overpeak when surprised.",
                rounds=rounds,
                source_module=self.name,
            ))
        
        return feedbacks

"""Utility Intelligence Module."""

from dataclasses import dataclass, field
from typing import Optional

from src.models import (
    DemoData, RoundData, FlashEvent, SmokeEvent, UtilityEvent,
    Team, Vector3
)
from src.intelligence.base import (
    IntelligenceModule, ModuleResult, ModuleScore,
    Feedback, FeedbackCategory, FeedbackSeverity
)


@dataclass
class FlashAnalysis:
    """Analysis of a flash throw."""
    tick: int
    round_number: int
    thrower_id: str
    
    enemies_blinded: int = 0
    teammates_blinded: int = 0
    self_flash: bool = False
    avg_blind_duration: float = 0.0
    full_blinds: int = 0  # >2s duration
    
    # ROI: positive = good, negative = hurt team
    flash_roi: float = 0.0


@dataclass
class SmokeAnalysis:
    """Analysis of a smoke throw."""
    tick: int
    round_number: int
    thrower_id: str
    
    blocks_sightline: bool = False
    timing_good: bool = False
    wasted: bool = False


@dataclass
class UtilityAnalysisResult:
    """Complete utility analysis for a player."""
    flashes: list[FlashAnalysis] = field(default_factory=list)
    smokes: list[SmokeAnalysis] = field(default_factory=list)
    
    total_flashes: int = 0
    effective_flashes: int = 0
    self_flashes: int = 0
    team_flashes: int = 0
    
    flash_roi: float = 0.0
    utility_score: float = 0.0


class UtilityIntelligenceModule(IntelligenceModule):
    """
    Analyzes utility effectiveness.
    
    For flashes:
    - Enemies blinded vs teammates/self
    - Blind duration
    - Flash ROI
    
    For smokes:
    - Sightline blocking
    - Timing vs enemy push
    
    Output:
    - Utility ROI score
    - Team synergy %
    """
    
    name = "utility_intelligence"
    version = "1.0.0"
    
    # Flash scoring
    ENEMY_BLIND_POINTS = 20.0  # Per enemy blinded
    TEAMMATE_BLIND_PENALTY = -15.0
    SELF_FLASH_PENALTY = -25.0
    FULL_BLIND_BONUS = 10.0  # >2s duration
    
    def analyze(self, demo_data: DemoData, player_id: str) -> ModuleResult:
        """Analyze utility usage for a player."""
        flash_analyses: list[FlashAnalysis] = []
        smoke_analyses: list[SmokeAnalysis] = []
        
        for round_data in demo_data.rounds:
            # Find flash events from this player
            for event in round_data.events:
                if isinstance(event, FlashEvent):
                    if event.thrower_id == player_id:
                        analysis = self._analyze_flash(event, round_data)
                        flash_analyses.append(analysis)
                
                elif isinstance(event, SmokeEvent):
                    if event.thrower_id == player_id:
                        analysis = self._analyze_smoke(event, round_data)
                        smoke_analyses.append(analysis)
        
        # Compute aggregate stats
        result = self._aggregate_results(flash_analyses, smoke_analyses)
        score = self._compute_score(result)
        feedbacks = self._generate_feedback(result)
        
        return ModuleResult(
            module_name=self.name,
            score=score,
            feedbacks=feedbacks,
            raw_data={
                "flash_analyses": flash_analyses,
                "smoke_analyses": smoke_analyses,
                "result": result
            }
        )
    
    def _analyze_flash(self, flash: FlashEvent, round_data: RoundData) -> FlashAnalysis:
        """Analyze a single flash throw."""
        # Calculate ROI
        roi = 0.0
        roi += flash.enemies_blinded * self.ENEMY_BLIND_POINTS
        roi += flash.teammates_blinded * self.TEAMMATE_BLIND_PENALTY
        
        if flash.self_flash:
            roi += self.SELF_FLASH_PENALTY
        
        # Bonus for full blinds (>2s)
        if flash.avg_blind_duration > 2.0:
            roi += self.FULL_BLIND_BONUS * flash.enemies_blinded
        
        full_blinds = 1 if flash.avg_blind_duration > 2.0 and flash.enemies_blinded > 0 else 0
        
        return FlashAnalysis(
            tick=flash.tick,
            round_number=round_data.round_number,
            thrower_id=flash.thrower_id,
            enemies_blinded=flash.enemies_blinded,
            teammates_blinded=flash.teammates_blinded,
            self_flash=flash.self_flash,
            avg_blind_duration=flash.avg_blind_duration,
            full_blinds=full_blinds,
            flash_roi=roi,
        )
    
    def _analyze_smoke(self, smoke: SmokeEvent, round_data: RoundData) -> SmokeAnalysis:
        """Analyze a single smoke throw."""
        # Simplified: assume smoke is useful if thrown mid-round
        mid_round_tick = round_data.start_tick + (round_data.end_tick - round_data.start_tick) // 3
        
        timing_good = smoke.tick > mid_round_tick
        wasted = smoke.tick < round_data.start_tick + 128  # Too early
        
        return SmokeAnalysis(
            tick=smoke.tick,
            round_number=round_data.round_number,
            thrower_id=smoke.thrower_id,
            blocks_sightline=True,  # Assume good placement
            timing_good=timing_good,
            wasted=wasted,
        )
    
    def _aggregate_results(
        self,
        flashes: list[FlashAnalysis],
        smokes: list[SmokeAnalysis]
    ) -> UtilityAnalysisResult:
        """Aggregate utility analysis results."""
        total_flashes = len(flashes)
        effective_flashes = sum(1 for f in flashes if f.enemies_blinded > 0)
        self_flashes = sum(1 for f in flashes if f.self_flash)
        team_flashes = sum(1 for f in flashes if f.teammates_blinded > 0 and not f.self_flash)
        
        total_roi = sum(f.flash_roi for f in flashes)
        avg_roi = total_roi / total_flashes if total_flashes > 0 else 0
        
        # Utility score (0-100)
        if total_flashes == 0:
            utility_score = 50.0  # Neutral if no utility used
        else:
            effectiveness_rate = effective_flashes / total_flashes
            self_flash_rate = self_flashes / total_flashes
            
            utility_score = (effectiveness_rate * 70) + ((1 - self_flash_rate) * 30)
            utility_score = max(0, min(100, utility_score))
        
        return UtilityAnalysisResult(
            flashes=flashes,
            smokes=smokes,
            total_flashes=total_flashes,
            effective_flashes=effective_flashes,
            self_flashes=self_flashes,
            team_flashes=team_flashes,
            flash_roi=avg_roi,
            utility_score=utility_score,
        )
    
    def _compute_score(self, result: UtilityAnalysisResult) -> ModuleScore:
        """Compute utility intelligence score."""
        return ModuleScore(
            module_name=self.name,
            overall_score=result.utility_score,
            components={
                "total_flashes": result.total_flashes,
                "effective_flashes": result.effective_flashes,
                "self_flashes": result.self_flashes,
                "team_flashes": result.team_flashes,
                "flash_roi": result.flash_roi,
            }
        )
    
    def _generate_feedback(self, result: UtilityAnalysisResult) -> list[Feedback]:
        """Generate utility feedback."""
        feedbacks: list[Feedback] = []
        
        # Self-flash problem
        if result.self_flashes >= 2:
            rounds = list(set(f.round_number for f in result.flashes if f.self_flash))
            feedbacks.append(Feedback(
                category=FeedbackCategory.TACTICAL,
                severity=FeedbackSeverity.MAJOR,
                priority=3,
                title=f"Self-flashed {result.self_flashes}x",
                description=f"You blinded yourself {result.self_flashes} times during the match.",
                fix="Turn from your flash before it pops, or delay your peek.",
                rounds=rounds,
                source_module=self.name,
            ))
        
        # Team flash problem
        if result.team_flashes >= 3:
            rounds = list(set(f.round_number for f in result.flashes if f.teammates_blinded > 0))
            feedbacks.append(Feedback(
                category=FeedbackCategory.TACTICAL,
                severity=FeedbackSeverity.MAJOR,
                priority=4,
                title=f"Flashed teammates {result.team_flashes}x",
                description="You're consistently blinding your own team.",
                fix="Communicate flash timing. Use different pop angles.",
                rounds=rounds,
                source_module=self.name,
            ))
        
        # Low utility effectiveness
        if result.total_flashes >= 5 and result.effective_flashes / result.total_flashes < 0.3:
            feedbacks.append(Feedback(
                category=FeedbackCategory.TACTICAL,
                severity=FeedbackSeverity.MINOR,
                priority=6,
                title=f"Low flash effectiveness: {result.effective_flashes}/{result.total_flashes}",
                description="Most of your flashes aren't hitting enemies.",
                fix="Learn pop flash lineups for common positions.",
                source_module=self.name,
            ))
        
        return feedbacks
    
    def generate_feedback(self, result: ModuleResult) -> list[Feedback]:
        return result.feedbacks

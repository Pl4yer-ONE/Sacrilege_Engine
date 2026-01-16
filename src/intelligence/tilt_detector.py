"""Tilt Detector Module."""

from dataclasses import dataclass, field
from typing import Optional
import statistics

from src.models import DemoData, RoundData, KillEvent, Team, Vector3
from src.intelligence.base import (
    IntelligenceModule, ModuleResult, ModuleScore,
    Feedback, FeedbackCategory, FeedbackSeverity
)


@dataclass
class RoundTiltIndicators:
    """Tilt indicators for a single round."""
    round_number: int
    
    solo_pushes: int = 0
    deaths_early: int = 0  # Died in first 30s of round
    position_variance: float = 0.0
    
    # Normalized tilt score for this round (0-100, higher = more tilted)
    tilt_score: float = 0.0


@dataclass
class TiltAnalysisResult:
    """Complete tilt analysis for a player."""
    round_indicators: list[RoundTiltIndicators] = field(default_factory=list)
    
    tilt_detected: bool = False
    tilt_start_round: Optional[int] = None
    severity_pct: float = 0.0
    
    # Patterns
    solo_push_rounds: list[int] = field(default_factory=list)
    early_death_rounds: list[int] = field(default_factory=list)


class TiltDetectorModule(IntelligenceModule):
    """
    Detects mental state degradation.
    
    Indicators:
    - Repeated solo pushes
    - Early round deaths
    - Position randomness (not holding normal spots)
    - Spray pattern degradation (would need more data)
    
    Output:
    - Tilt start round
    - Severity %
    """
    
    name = "tilt_detector"
    version = "1.0.0"
    
    # Thresholds
    EARLY_DEATH_THRESHOLD_TICKS = 30 * 64  # First 30s at 64 tick
    TILT_SCORE_THRESHOLD = 60.0  # Above this = tilted
    CONSECUTIVE_BAD_ROUNDS = 3  # Need this many to confirm tilt
    
    def analyze(self, demo_data: DemoData, player_id: str) -> ModuleResult:
        """Analyze tilt indicators for a player."""
        player_info = demo_data.players.get(player_id)
        if not player_info:
            return ModuleResult(
                module_name=self.name,
                score=ModuleScore(module_name=self.name, overall_score=100.0)
            )
        
        player_team = player_info.team
        round_indicators: list[RoundTiltIndicators] = []
        
        for round_data in demo_data.rounds:
            indicators = self._analyze_round(
                round_data, demo_data, player_id, player_team
            )
            round_indicators.append(indicators)
        
        # Detect tilt onset
        result = self._detect_tilt_onset(round_indicators)
        score = self._compute_score(result)
        feedbacks = self._generate_feedback(result)
        
        return ModuleResult(
            module_name=self.name,
            score=score,
            feedbacks=feedbacks,
            raw_data={"result": result}
        )
    
    def _analyze_round(
        self,
        round_data: RoundData,
        demo_data: DemoData,
        player_id: str,
        player_team: Team
    ) -> RoundTiltIndicators:
        """Analyze tilt indicators for a single round."""
        solo_pushes = 0
        deaths_early = 0
        
        # Check for early deaths
        for kill in round_data.kills:
            if kill.victim_id == player_id:
                time_since_start = kill.tick - round_data.start_tick
                if time_since_start < self.EARLY_DEATH_THRESHOLD_TICKS:
                    deaths_early += 1
        
        # Check for solo pushes (died without teammates nearby)
        # Simplified: count deaths where no teammates got kills nearby
        player_deaths = [k for k in round_data.kills if k.victim_id == player_id]
        
        for death in player_deaths:
            # Check if any teammate killed something within 3s
            trade_window = 3 * 64  # 3 seconds at 64 tick
            teammate_kills = [
                k for k in round_data.kills
                if k.attacker_id != player_id
                and k.attacker_id in demo_data.players
                and demo_data.players[k.attacker_id].team == player_team
                and abs(k.tick - death.tick) < trade_window
            ]
            
            if not teammate_kills:
                solo_pushes += 1
        
        # Compute tilt score for this round
        tilt_score = 0.0
        tilt_score += solo_pushes * 30
        tilt_score += deaths_early * 25
        tilt_score = min(100, tilt_score)
        
        return RoundTiltIndicators(
            round_number=round_data.round_number,
            solo_pushes=solo_pushes,
            deaths_early=deaths_early,
            tilt_score=tilt_score,
        )
    
    def _detect_tilt_onset(
        self,
        indicators: list[RoundTiltIndicators]
    ) -> TiltAnalysisResult:
        """Detect when tilt started."""
        if not indicators:
            return TiltAnalysisResult()
        
        # Find first sequence of N consecutive high-tilt rounds
        tilt_start = None
        consecutive_high = 0
        
        for ind in indicators:
            if ind.tilt_score >= self.TILT_SCORE_THRESHOLD:
                consecutive_high += 1
                if consecutive_high >= self.CONSECUTIVE_BAD_ROUNDS and tilt_start is None:
                    tilt_start = ind.round_number - self.CONSECUTIVE_BAD_ROUNDS + 1
            else:
                consecutive_high = 0
        
        # Calculate severity
        if tilt_start:
            post_tilt = [i for i in indicators if i.round_number >= tilt_start]
            avg_tilt = sum(i.tilt_score for i in post_tilt) / len(post_tilt) if post_tilt else 0
            severity = min(100, avg_tilt)
        else:
            severity = 0.0
        
        # Collect pattern rounds
        solo_push_rounds = [i.round_number for i in indicators if i.solo_pushes > 0]
        early_death_rounds = [i.round_number for i in indicators if i.deaths_early > 0]
        
        return TiltAnalysisResult(
            round_indicators=indicators,
            tilt_detected=tilt_start is not None,
            tilt_start_round=tilt_start,
            severity_pct=severity,
            solo_push_rounds=solo_push_rounds,
            early_death_rounds=early_death_rounds,
        )
    
    def _compute_score(self, result: TiltAnalysisResult) -> ModuleScore:
        """Compute mental stability score (inverse of tilt)."""
        # Higher score = more stable (less tilted)
        if result.tilt_detected:
            score = 100 - result.severity_pct
        else:
            # No tilt detected
            avg_tilt = sum(i.tilt_score for i in result.round_indicators) / len(result.round_indicators) if result.round_indicators else 0
            score = 100 - avg_tilt
        
        return ModuleScore(
            module_name=self.name,
            overall_score=max(0, score),
            components={
                "tilt_detected": 1 if result.tilt_detected else 0,
                "tilt_start_round": result.tilt_start_round or 0,
                "severity_pct": result.severity_pct,
                "solo_push_count": len(result.solo_push_rounds),
                "early_death_count": len(result.early_death_rounds),
            }
        )
    
    def _generate_feedback(self, result: TiltAnalysisResult) -> list[Feedback]:
        """Generate tilt feedback."""
        feedbacks: list[Feedback] = []
        
        if result.tilt_detected:
            feedbacks.append(Feedback(
                category=FeedbackCategory.MENTAL,
                severity=FeedbackSeverity.CRITICAL,
                priority=2,
                title=f"Tilt detected at Round {result.tilt_start_round}",
                description=f"Your play degraded significantly after R{result.tilt_start_round}. Severity: {result.severity_pct:.0f}%",
                fix="Take a breath after bad rounds. Don't change your playstyle when losing.",
                rounds=[result.tilt_start_round],
                source_module=self.name,
            ))
        
        # Solo push pattern
        if len(result.solo_push_rounds) >= 3:
            feedbacks.append(Feedback(
                category=FeedbackCategory.MENTAL,
                severity=FeedbackSeverity.MAJOR,
                priority=3,
                title=f"Solo push pattern: {len(result.solo_push_rounds)} rounds",
                description="You repeatedly pushed alone without team support.",
                fix="Wait for teammates. Call your pushes.",
                rounds=result.solo_push_rounds[:5],  # First 5
                source_module=self.name,
            ))
        
        # Early death pattern
        if len(result.early_death_rounds) >= 3:
            feedbacks.append(Feedback(
                category=FeedbackCategory.TACTICAL,
                severity=FeedbackSeverity.MAJOR,
                priority=4,
                title=f"Early deaths: {len(result.early_death_rounds)} rounds",
                description="You died in the first 30 seconds too often.",
                fix="Play slower in early round. Let entries go first.",
                rounds=result.early_death_rounds[:5],
                source_module=self.name,
            ))
        
        return feedbacks
    
    def generate_feedback(self, result: ModuleResult) -> list[Feedback]:
        return result.feedbacks

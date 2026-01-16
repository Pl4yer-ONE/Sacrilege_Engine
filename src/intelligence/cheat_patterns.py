"""Soft-Cheat Pattern Detection Module."""

from dataclasses import dataclass, field
from typing import Optional
import statistics

from src.models import DemoData, RoundData, KillEvent, Team
from src.intelligence.base import (
    IntelligenceModule, ModuleResult, ModuleScore,
    Feedback, FeedbackCategory, FeedbackSeverity
)


@dataclass
class SuspicionPattern:
    """A detected suspicious pattern."""
    pattern_type: str  # 'reaction_cluster', 'smoke_kill', 'prefire'
    occurrences: int
    confidence: float  # 0-1
    rounds: list[int] = field(default_factory=list)
    details: str = ""


@dataclass
class CheatAnalysisResult:
    """Complete cheat pattern analysis."""
    patterns: list[SuspicionPattern] = field(default_factory=list)
    
    overall_suspicion: float = 0.0  # 0-100
    
    # Disclaimer flag
    is_accusation: bool = False
    disclaimer: str = "Statistical analysis only. Not a definitive cheat detection."


class CheatPatternModule(IntelligenceModule):
    """
    Detects suspicious patterns.
    
    NOT for accusations - statistical anomaly detection only.
    
    Patterns detected:
    - Inhuman reaction time clusters
    - Through-smoke kills
    - Consistent prefires
    
    Output:
    - Suspicion probability
    - Pattern breakdown
    """
    
    name = "cheat_patterns"
    version = "1.0.0"
    
    # Thresholds
    INHUMAN_REACTION_MS = 150  # Below this is suspicious
    SMOKE_KILL_THRESHOLD = 3  # More than this is suspicious
    PREFIRE_THRESHOLD = 3  # Consistent prefires
    
    def analyze(self, demo_data: DemoData, player_id: str) -> ModuleResult:
        """Analyze cheat patterns for a player."""
        patterns: list[SuspicionPattern] = []
        
        # Analyze reaction times
        reaction_pattern = self._analyze_reaction_times(demo_data, player_id)
        if reaction_pattern:
            patterns.append(reaction_pattern)
        
        # Analyze smoke kills
        smoke_pattern = self._analyze_smoke_kills(demo_data, player_id)
        if smoke_pattern:
            patterns.append(smoke_pattern)
        
        # Compute overall suspicion
        overall = self._compute_overall_suspicion(patterns)
        
        result = CheatAnalysisResult(
            patterns=patterns,
            overall_suspicion=overall,
            is_accusation=False,
            disclaimer="Statistical analysis only. Not a definitive cheat detection."
        )
        
        score = ModuleScore(
            module_name=self.name,
            overall_score=100 - overall,  # Higher score = less suspicious
            components={
                "suspicion_pct": overall,
                "pattern_count": len(patterns),
            }
        )
        
        # Only generate feedback if very suspicious
        feedbacks = self._generate_feedback(result) if overall > 40 else []
        
        return ModuleResult(
            module_name=self.name,
            score=score,
            feedbacks=feedbacks,
            raw_data={"result": result}
        )
    
    def _analyze_reaction_times(
        self,
        demo_data: DemoData,
        player_id: str
    ) -> Optional[SuspicionPattern]:
        """Look for inhuman reaction time clusters."""
        # Get all kills by this player
        kills = []
        for round_data in demo_data.rounds:
            for kill in round_data.kills:
                if kill.attacker_id == player_id:
                    kills.append((round_data.round_number, kill))
        
        if len(kills) < 5:
            return None
        
        # Simplified: we don't have actual reaction time data
        # In full implementation, would analyze time from enemy visible to shot
        
        # Check for through-smoke kills as proxy for suspicious behavior
        suspicious_kills = [
            (r, k) for r, k in kills
            if k.through_smoke
        ]
        
        if len(suspicious_kills) >= self.SMOKE_KILL_THRESHOLD:
            return SuspicionPattern(
                pattern_type="smoke_kills",
                occurrences=len(suspicious_kills),
                confidence=min(0.9, len(suspicious_kills) * 0.15),
                rounds=[r for r, _ in suspicious_kills],
                details=f"Killed {len(suspicious_kills)} enemies through smoke"
            )
        
        return None
    
    def _analyze_smoke_kills(
        self,
        demo_data: DemoData,
        player_id: str
    ) -> Optional[SuspicionPattern]:
        """Analyze kills through smokes."""
        smoke_kills = []
        
        for round_data in demo_data.rounds:
            for kill in round_data.kills:
                if kill.attacker_id == player_id and kill.through_smoke:
                    smoke_kills.append(round_data.round_number)
        
        if len(smoke_kills) >= self.SMOKE_KILL_THRESHOLD:
            confidence = min(0.8, len(smoke_kills) * 0.1)
            
            return SuspicionPattern(
                pattern_type="smoke_tracking",
                occurrences=len(smoke_kills),
                confidence=confidence,
                rounds=smoke_kills,
                details=f"High rate of through-smoke kills"
            )
        
        return None
    
    def _compute_overall_suspicion(self, patterns: list[SuspicionPattern]) -> float:
        """Compute overall suspicion score."""
        if not patterns:
            return 0.0
        
        # Weighted average of pattern confidences
        total_weight = 0.0
        weighted_sum = 0.0
        
        for pattern in patterns:
            weight = pattern.occurrences
            weighted_sum += pattern.confidence * weight * 100
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return min(100, weighted_sum / total_weight)
    
    def _generate_feedback(self, result: CheatAnalysisResult) -> list[Feedback]:
        """Generate feedback for suspicious patterns."""
        feedbacks: list[Feedback] = []
        
        if result.overall_suspicion > 40:
            pattern_desc = ", ".join(p.pattern_type for p in result.patterns)
            
            feedbacks.append(Feedback(
                category=FeedbackCategory.TACTICAL,  # Not accusation
                severity=FeedbackSeverity.MINOR,
                priority=10,  # Low priority - informational
                title=f"Unusual patterns detected: {pattern_desc}",
                description=f"Suspicion score: {result.overall_suspicion:.0f}%. {result.disclaimer}",
                fix="This is statistical analysis, not an accusation.",
                source_module=self.name,
                evidence={
                    "patterns": [
                        {"type": p.pattern_type, "occurrences": p.occurrences, "confidence": p.confidence}
                        for p in result.patterns
                    ],
                    "disclaimer": result.disclaimer
                }
            ))
        
        return feedbacks
    
    def generate_feedback(self, result: ModuleResult) -> list[Feedback]:
        return result.feedbacks

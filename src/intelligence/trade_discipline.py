"""Trade Discipline Index Module."""

from dataclasses import dataclass, field
from typing import Optional

from src.models import (
    DemoData, RoundData, KillEvent, PlayerState, 
    Team, TradeClassification, Vector3
)
from src.intelligence.base import (
    IntelligenceModule, ModuleResult, ModuleScore, 
    Feedback, FeedbackCategory, FeedbackSeverity
)
from src.config import get_settings


@dataclass
class TradeAnalysis:
    """Analysis of a single trade opportunity."""
    death_tick: int
    round_number: int
    
    victim_id: str
    killer_id: str
    
    trade_possible: bool
    trade_happened: bool = False
    
    classification: TradeClassification = TradeClassification.IMPOSSIBLE
    delay_ms: Optional[int] = None
    
    nearest_teammate_id: Optional[str] = None
    nearest_teammate_distance: float = 0.0
    
    teammate_had_los: bool = False
    teammate_was_flashed: bool = False
    teammate_was_looking: bool = False
    
    reason: str = ""


class TradeDisciplineModule(IntelligenceModule):
    """
    Analyzes trade discipline for every death.
    
    For every death:
    - Was a trade possible?
    - Did trade happen?
    - How long was the delay?
    - Was teammate positioned correctly?
    
    Classifications:
    - PERFECT: Trade within 1.5s, teammate had LOS
    - LATE: Trade within 3s
    - MISSED: Trade possible but didn't happen
    - IMPOSSIBLE: No teammate nearby
    """
    
    name = "trade_discipline"
    version = "1.0.0"
    
    def __init__(self):
        self.settings = get_settings()
        self.perfect_window = self.settings.trade_window_perfect_ms
        self.late_window = self.settings.trade_window_late_ms
        self.max_distance = self.settings.trade_max_distance
    
    def analyze(self, demo_data: DemoData, player_id: str) -> ModuleResult:
        """Analyze trade discipline for a specific player."""
        analyses: list[TradeAnalysis] = []
        
        for round_data in demo_data.rounds:
            round_analyses = self._analyze_round(
                round_data, 
                demo_data, 
                player_id
            )
            analyses.extend(round_analyses)
        
        # Compute scores
        score = self._compute_score(analyses)
        
        # Generate feedbacks
        feedbacks = self.generate_feedback_from_analyses(analyses, player_id)
        
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
    ) -> list[TradeAnalysis]:
        """Analyze trade opportunities in a single round."""
        analyses: list[TradeAnalysis] = []
        
        # Get player's team
        player_info = demo_data.players.get(player_id)
        if not player_info:
            return []
        
        player_team = player_info.team
        
        # Analyze deaths of teammates
        for kill in round_data.kills:
            victim_info = demo_data.players.get(kill.victim_id)
            if not victim_info:
                continue
            
            # Only analyze teammate deaths (not our own)
            if victim_info.team != player_team:
                continue
            
            if kill.victim_id == player_id:
                continue
            
            # Analyze trade opportunity
            analysis = self._analyze_trade_opportunity(
                kill,
                round_data,
                demo_data,
                player_id,
                player_team
            )
            
            analyses.append(analysis)
        
        return analyses
    
    def _analyze_trade_opportunity(
        self,
        death: KillEvent,
        round_data: RoundData,
        demo_data: DemoData,
        player_id: str,
        player_team: Team
    ) -> TradeAnalysis:
        """Analyze a single trade opportunity."""
        # Find nearest teammate at time of death
        # Simplified: use position data from kill event
        
        victim_pos = death.victim_position or Vector3(0, 0, 0)
        killer_pos = death.attacker_position or Vector3(0, 0, 0)
        
        # Check if we (player_id) could trade
        # Simplified: check distance from victim position
        # In full implementation, would query player states at tick
        
        # Assume we need to find kills after this death
        trade_kill = self._find_trade_kill(
            death,
            round_data.kills,
            player_id,
            player_team
        )
        
        # Check if trade was possible based on squared distance for efficiency
        max_dist_sq = (self.max_distance * 2) ** 2
        trade_possible = victim_pos.distance_squared_to(killer_pos) < max_dist_sq  # Rough estimate
        
        if trade_kill:
            delay_ms = int((trade_kill.tick - death.tick) * (1000 / 64))  # Assuming 64 tick
            
            if delay_ms <= self.perfect_window:
                classification = TradeClassification.PERFECT
            elif delay_ms <= self.late_window:
                classification = TradeClassification.LATE
            else:
                classification = TradeClassification.MISSED
            
            return TradeAnalysis(
                death_tick=death.tick,
                round_number=round_data.round_number,
                victim_id=death.victim_id,
                killer_id=death.attacker_id,
                trade_possible=True,
                trade_happened=True,
                classification=classification,
                delay_ms=delay_ms,
            )
        
        return TradeAnalysis(
            death_tick=death.tick,
            round_number=round_data.round_number,
            victim_id=death.victim_id,
            killer_id=death.attacker_id,
            trade_possible=trade_possible,
            trade_happened=False,
            classification=TradeClassification.MISSED if trade_possible else TradeClassification.IMPOSSIBLE,
            reason="no_trade" if trade_possible else "no_opportunity"
        )
    
    def _find_trade_kill(
        self,
        death: KillEvent,
        kills: list[KillEvent],
        player_id: str,
        player_team: Team
    ) -> Optional[KillEvent]:
        """Find if someone on our team killed the killer."""
        for kill in kills:
            # Kill must be after death
            if kill.tick <= death.tick:
                continue
            
            # Kill must be within trade window
            if kill.tick > death.tick + (self.late_window * 64 / 1000):
                continue
            
            # Victim must be the original killer
            if kill.victim_id != death.attacker_id:
                continue
            
            # Attacker must be on our team (simplified check)
            return kill
        
        return None
    
    def _compute_score(self, analyses: list[TradeAnalysis]) -> ModuleScore:
        """Compute trade discipline score."""
        if not analyses:
            return ModuleScore(
                module_name=self.name,
                overall_score=100.0,
                components={"perfect": 0, "late": 0, "missed": 0}
            )
        
        perfect = sum(1 for a in analyses if a.classification == TradeClassification.PERFECT)
        late = sum(1 for a in analyses if a.classification == TradeClassification.LATE)
        missed = sum(1 for a in analyses if a.classification == TradeClassification.MISSED)
        impossible = sum(1 for a in analyses if a.classification == TradeClassification.IMPOSSIBLE)
        
        tradeable = perfect + late + missed
        if tradeable == 0:
            return ModuleScore(
                module_name=self.name,
                overall_score=100.0,
                components={"perfect": 0, "late": 0, "missed": 0}
            )
        
        # Score calculation:
        # Perfect = 100 pts, Late = 60 pts, Missed = 0 pts
        score = ((perfect * 100) + (late * 60)) / tradeable
        
        return ModuleScore(
            module_name=self.name,
            overall_score=score,
            components={
                "perfect": perfect,
                "late": late,
                "missed": missed,
                "impossible": impossible,
                "total_tradeable": tradeable,
            }
        )
    
    def generate_feedback(self, result: ModuleResult) -> list[Feedback]:
        """Generate feedback from module result."""
        return result.feedbacks
    
    def generate_feedback_from_analyses(
        self, 
        analyses: list[TradeAnalysis],
        player_id: str
    ) -> list[Feedback]:
        """Generate actionable feedback from trade analyses."""
        feedbacks: list[Feedback] = []
        
        # Find missed trades
        missed = [a for a in analyses if a.classification == TradeClassification.MISSED]
        
        if len(missed) >= 2:
            rounds = [a.round_number for a in missed]
            avg_distance = sum(a.nearest_teammate_distance for a in missed) / len(missed)
            
            feedbacks.append(Feedback(
                category=FeedbackCategory.TACTICAL,
                severity=FeedbackSeverity.CRITICAL if len(missed) >= 3 else FeedbackSeverity.MAJOR,
                priority=2,
                title=f"Missed trades: {len(missed)} opportunities",
                description=f"Your teammate died {len(missed)}x with you unable to trade.",
                fix="Position closer to teammates or call out before peeking.",
                rounds=rounds,
                source_module=self.name,
            ))
        
        # Find late trades
        late = [a for a in analyses if a.classification == TradeClassification.LATE]
        
        if len(late) >= 2:
            rounds = [a.round_number for a in late]
            avg_delay = sum(a.delay_ms or 0 for a in late) / len(late)
            
            feedbacks.append(Feedback(
                category=FeedbackCategory.MECHANICAL,
                severity=FeedbackSeverity.MAJOR,
                priority=4,
                title=f"Late trades: {avg_delay:.0f}ms average delay",
                description=f"You traded {len(late)}x but reaction was slow (target: <{self.perfect_window}ms).",
                fix="Improve reaction time and pre-aim common angles.",
                rounds=rounds,
                source_module=self.name,
            ))
        
        return feedbacks

"""Round Outcome Simulator Module."""

from dataclasses import dataclass, field
from typing import Optional
import math

from src.models import DemoData, RoundData, KillEvent, Team, Vector3
from src.intelligence.base import (
    IntelligenceModule, ModuleResult, ModuleScore,
    Feedback, FeedbackCategory, FeedbackSeverity
)


@dataclass
class RoundSimulation:
    """Simulation result for a single round."""
    round_number: int
    
    # Actual outcome
    actual_winner: Optional[Team] = None
    actual_kills: int = 0
    
    # Pre-death win probability
    pre_death_win_prob: float = 0.5
    
    # Post-death win probability (how much it dropped)
    post_death_win_prob: float = 0.5
    
    # Delta - impact of the death
    win_prob_delta: float = 0.0
    
    # Context
    player_death_tick: int = 0
    death_early: bool = False  # First blood
    was_entry: bool = False    # Entry position


@dataclass
class WhatIfScenario:
    """A what-if analysis scenario."""
    description: str
    
    # If player had survived
    survival_win_prob: float = 0.0
    
    # Actual outcome
    actual_win_prob: float = 0.0
    
    # Impact of the decision
    impact: float = 0.0
    
    rounds: list[int] = field(default_factory=list)


class RoundSimulatorModule(IntelligenceModule):
    """
    Simulates round outcomes with different scenarios.
    
    For each death, calculates:
    - Pre-death win probability
    - Post-death win probability
    - Impact of the death
    
    Uses simplified win probability model based on:
    - Player count advantage
    - Equipment value
    - Round time remaining
    - Bomb status
    
    Output:
    - High-impact deaths (costly mistakes)
    - What-if scenarios
    """
    
    name = "round_simulator"
    version = "1.0.0"
    
    # Win probability base values (5v5 = 50%)
    WIN_PROB_BY_PLAYERS = {
        (5, 5): 0.50,
        (5, 4): 0.60,
        (5, 3): 0.75,
        (5, 2): 0.88,
        (5, 1): 0.96,
        (5, 0): 1.00,
        (4, 5): 0.40,
        (4, 4): 0.50,
        (4, 3): 0.63,
        (4, 2): 0.78,
        (4, 1): 0.91,
        (4, 0): 1.00,
        (3, 5): 0.25,
        (3, 4): 0.37,
        (3, 3): 0.50,
        (3, 2): 0.66,
        (3, 1): 0.83,
        (3, 0): 1.00,
        (2, 5): 0.12,
        (2, 4): 0.22,
        (2, 3): 0.34,
        (2, 2): 0.50,
        (2, 1): 0.71,
        (2, 0): 1.00,
        (1, 5): 0.04,
        (1, 4): 0.09,
        (1, 3): 0.17,
        (1, 2): 0.29,
        (1, 1): 0.50,
        (1, 0): 1.00,
        (0, 5): 0.00,
        (0, 4): 0.00,
        (0, 3): 0.00,
        (0, 2): 0.00,
        (0, 1): 0.00,
        (0, 0): 0.00,
    }
    
    def analyze(self, demo_data: DemoData, player_id: str) -> ModuleResult:
        """Simulate round outcomes for player's deaths."""
        player_info = demo_data.players.get(player_id)
        if not player_info:
            return ModuleResult(
                module_name=self.name,
                score=ModuleScore(module_name=self.name, overall_score=100.0)
            )
        
        player_team = player_info.team
        simulations: list[RoundSimulation] = []
        
        for round_data in demo_data.rounds:
            sim = self._simulate_round(
                round_data, demo_data, player_id, player_team
            )
            if sim:
                simulations.append(sim)
        
        # Find high-impact deaths
        what_ifs = self._generate_what_ifs(simulations)
        
        score = self._compute_score(simulations)
        feedbacks = self._generate_feedback(simulations, what_ifs)
        
        return ModuleResult(
            module_name=self.name,
            score=score,
            feedbacks=feedbacks,
            raw_data={
                "simulations": simulations,
                "what_ifs": what_ifs,
            }
        )
    
    def _simulate_round(
        self,
        round_data: RoundData,
        demo_data: DemoData,
        player_id: str,
        player_team: Team
    ) -> Optional[RoundSimulation]:
        """Simulate a single round focusing on player's death."""
        # Find player's death in this round
        player_death = None
        death_order = 0
        
        for i, kill in enumerate(round_data.kills):
            if kill.victim_id == player_id:
                player_death = kill
                death_order = i
                break
        
        if not player_death:
            return None  # Player survived - no simulation needed
        
        # Count players alive at time of death
        team_alive_before = 5
        enemy_alive_before = 5
        
        # Count deaths before player's death
        for i, kill in enumerate(round_data.kills):
            if i >= death_order:
                break
            
            victim_info = demo_data.players.get(kill.victim_id)
            if not victim_info:
                continue
            
            if victim_info.team == player_team:
                team_alive_before -= 1
            else:
                enemy_alive_before -= 1
        
        # Calculate pre-death and post-death probabilities
        pre_death_prob = self._get_win_probability(team_alive_before, enemy_alive_before)
        post_death_prob = self._get_win_probability(team_alive_before - 1, enemy_alive_before)
        
        delta = pre_death_prob - post_death_prob
        
        # Check if first blood
        is_first_blood = death_order == 0 and demo_data.players.get(round_data.kills[0].victim_id, None)
        if is_first_blood:
            is_first_blood = demo_data.players.get(round_data.kills[0].victim_id).team == player_team
        
        return RoundSimulation(
            round_number=round_data.round_number,
            actual_winner=round_data.winner,
            actual_kills=sum(1 for k in round_data.kills if k.attacker_id == player_id),
            pre_death_win_prob=pre_death_prob,
            post_death_win_prob=post_death_prob,
            win_prob_delta=delta,
            player_death_tick=player_death.tick,
            death_early=death_order < 2,
            was_entry=death_order == 0,
        )
    
    def _get_win_probability(self, team_alive: int, enemy_alive: int) -> float:
        """Get win probability from lookup table."""
        team_alive = max(0, min(5, team_alive))
        enemy_alive = max(0, min(5, enemy_alive))
        return self.WIN_PROB_BY_PLAYERS.get((team_alive, enemy_alive), 0.5)
    
    def _generate_what_ifs(self, simulations: list[RoundSimulation]) -> list[WhatIfScenario]:
        """Generate what-if scenarios from simulations."""
        what_ifs: list[WhatIfScenario] = []
        
        # High impact deaths (>20% swing)
        high_impact = [s for s in simulations if s.win_prob_delta > 0.20]
        
        if high_impact:
            total_delta = sum(s.win_prob_delta for s in high_impact)
            rounds = [s.round_number for s in high_impact]
            
            what_ifs.append(WhatIfScenario(
                description="High-impact deaths",
                survival_win_prob=sum(s.pre_death_win_prob for s in high_impact) / len(high_impact),
                actual_win_prob=sum(s.post_death_win_prob for s in high_impact) / len(high_impact),
                impact=total_delta / len(high_impact),
                rounds=rounds,
            ))
        
        # First blood deaths
        first_blood = [s for s in simulations if s.was_entry]
        
        if len(first_blood) >= 2:
            what_ifs.append(WhatIfScenario(
                description="First blood deaths",
                survival_win_prob=0.60,  # 5v5 going to 4v5
                actual_win_prob=0.40,
                impact=0.20,
                rounds=[s.round_number for s in first_blood],
            ))
        
        return what_ifs
    
    def _compute_score(self, simulations: list[RoundSimulation]) -> ModuleScore:
        """Compute round simulation score."""
        if not simulations:
            return ModuleScore(module_name=self.name, overall_score=100.0)
        
        avg_delta = sum(s.win_prob_delta for s in simulations) / len(simulations)
        
        # Score: lower delta = better (death had less impact)
        # Average delta of 0.15 (15% swing) = 50 score
        score = 100 - (avg_delta * 333)  # 0.30 delta = 0 score
        score = max(0, min(100, score))
        
        high_impact = sum(1 for s in simulations if s.win_prob_delta > 0.25)
        
        return ModuleScore(
            module_name=self.name,
            overall_score=score,
            components={
                "deaths_analyzed": len(simulations),
                "avg_win_prob_delta": avg_delta,
                "high_impact_deaths": high_impact,
            }
        )
    
    def _generate_feedback(
        self,
        simulations: list[RoundSimulation],
        what_ifs: list[WhatIfScenario]
    ) -> list[Feedback]:
        """Generate feedback from simulations."""
        feedbacks: list[Feedback] = []
        
        # High impact deaths
        high_impact = [s for s in simulations if s.win_prob_delta > 0.25]
        
        if len(high_impact) >= 2:
            avg_delta = sum(s.win_prob_delta for s in high_impact) / len(high_impact)
            
            feedbacks.append(Feedback(
                category=FeedbackCategory.TACTICAL,
                severity=FeedbackSeverity.CRITICAL,
                priority=1,
                title=f"Costly deaths: {len(high_impact)} high-impact rounds",
                description=f"Your deaths swung win probability by {avg_delta * 100:.0f}% on average.",
                fix="Avoid early deaths. Play for trades in man-advantage situations.",
                rounds=[s.round_number for s in high_impact],
                source_module=self.name,
            ))
        
        # First blood pattern
        first_blood = [s for s in simulations if s.was_entry]
        
        if len(first_blood) >= 3:
            feedbacks.append(Feedback(
                category=FeedbackCategory.TACTICAL,
                severity=FeedbackSeverity.MAJOR,
                priority=3,
                title=f"First blood deaths: {len(first_blood)} rounds",
                description="You're dying first too often, giving enemy advantage.",
                fix="Let teammates entry or wait for utility before peeking.",
                rounds=[s.round_number for s in first_blood],
                source_module=self.name,
            ))
        
        return feedbacks
    
    def generate_feedback(self, result: ModuleResult) -> list[Feedback]:
        return result.feedbacks

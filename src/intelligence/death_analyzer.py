# SPDX-FileCopyrightText: 2026 Pl4yer-ONE <mahadevan.rajeev27@gmail.com>
# SPDX-License-Identifier: LicenseRef-Sacrilege-EULA
#
# Sacrilege Engine - CS2 Demo Intelligence System
# https://github.com/Pl4yer-ONE/Sacrilege_Engine

"""
Death Analyzer Module - BRUTAL Edition
Comprehensive tactical mistake detection with performance ranking
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict
import math
from .llm_client import LLMClient


class MistakeType(Enum):
    """Types of tactical mistakes - BRUTAL classification."""
    # CRITICAL (5) - Complete tactical failure
    ISOLATED = "isolated"           # Died alone, no support possible
    CROSSFIRE = "crossfire"         # Exposed to multiple angles
    SOLO_PUSH = "solo_push"         # Pushed alone into enemy territory
    
    # SEVERE (4) - Major tactical error
    NO_TRADE = "no_trade"           # Teammate close but didn't trade
    WIDE_PEEK = "wide_peek"         # Over-extended peek
    UTILITY_DEATH = "utility"       # Died to/in utility
    
    # MODERATE (3) - Tactical mistake
    FLASHED = "flashed"             # Killed while blinded
    IN_MOLLY = "in_molly"           # Stupid fire death
    OUTNUMBERED = "outnumbered"     # Took bad fight
    REPEEKER = "repeeker"           # Re-peeked and died
    
    # MINOR (2) - Poor execution
    FIRST_CONTACT = "first"         # Entry death (acceptable)
    BAD_TIMING = "timing"           # Wrong timing
    
    # NEUTRAL (1) - Skill diff
    CLUTCH_ATTEMPT = "clutch"       # Died trying
    FAIR_DUEL = "fair_duel"         # Lost aim battle
    TRADED = "traded"               # At least got traded


@dataclass
class DeathAnalysis:
    """Complete death analysis result."""
    victim_name: str
    victim_team: str
    attacker_name: str
    tick: int
    round_num: int
    position: Tuple[float, float]
    mistakes: List[MistakeType]
    reasons: List[str]
    severity: int  # 1-5
    was_tradeable: bool
    was_traded: bool
    teammate_distance: float
    was_flashed: bool
    in_utility: bool
    enemy_count: int
    teammate_count: int
    
    def primary_mistake(self) -> MistakeType:
        """Get worst mistake."""
        priority = [
            MistakeType.ISOLATED,
            MistakeType.CROSSFIRE,
            MistakeType.SOLO_PUSH,
            MistakeType.NO_TRADE,
            MistakeType.WIDE_PEEK,
            MistakeType.UTILITY_DEATH,
            MistakeType.FLASHED,
            MistakeType.IN_MOLLY,
            MistakeType.OUTNUMBERED,
            MistakeType.REPEEKER,
            MistakeType.FIRST_CONTACT,
            MistakeType.BAD_TIMING,
            MistakeType.CLUTCH_ATTEMPT,
            MistakeType.TRADED,
            MistakeType.FAIR_DUEL,
        ]
        for m in priority:
            if m in self.mistakes:
                return m
        return self.mistakes[0] if self.mistakes else MistakeType.FAIR_DUEL
    
    def blame_score(self) -> float:
        """Calculate blame score (0-100). Higher = more at fault."""
        base = self.severity * 20
        
        # Modifiers
        if self.teammate_distance > 1000:
            base += 10  # Extra penalty for isolation
        if self.enemy_count >= 3:
            base -= 10  # Less blame if many enemies
        if self.was_traded:
            base -= 15  # Good if traded
        if self.was_flashed:
            base -= 5   # Slightly less blame
        
        return max(0, min(100, base))


@dataclass
class PlayerStats:
    """Live player performance stats."""
    name: str
    team: str
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    total_blame: float = 0
    mistake_counts: Dict[str, int] = field(default_factory=dict)
    death_analyses: List[DeathAnalysis] = field(default_factory=list)
    
    @property
    def kd_ratio(self) -> float:
        return self.kills / max(1, self.deaths)
    
    @property
    def avg_blame(self) -> float:
        if not self.death_analyses:
            return 0
        return sum(d.blame_score() for d in self.death_analyses) / len(self.death_analyses)
    
    @property
    def performance_score(self) -> float:
        """Overall performance: KD weighted by mistake severity."""
        kd_component = self.kd_ratio * 40
        blame_penalty = self.avg_blame * 0.4
        return max(0, kd_component - blame_penalty + 20)
    
    @property
    def rank_grade(self) -> str:
        """Letter grade based on performance."""
        score = self.performance_score
        if score >= 80: return "S"
        if score >= 65: return "A"
        if score >= 50: return "B"
        if score >= 35: return "C"
        if score >= 20: return "D"
        return "F"


class DeathAnalyzer:
    """BRUTAL death analyzer with live ranking."""
    
    # Thresholds
    ISOLATED_DISTANCE = 900
    CLOSE_SUPPORT = 400
    SOLO_PUSH_DISTANCE = 1200
    
    TRADE_WINDOW_TICKS = 192  # 3s
    FLASH_EFFECT_TICKS = 96   # 1.5s
    
    def __init__(self):
        self.death_history: List[DeathAnalysis] = []
        self.round_deaths: List[DeathAnalysis] = []
        self.current_round = 0
        self.round_death_order = 0
        
        # Player tracking
        self.player_stats: Dict[str, PlayerStats] = {}
        
        # Kill tracking for trade detection
        self.round_kills: List[dict] = []
        
    def analyze_death(
        self,
        kill_event: dict,
        players: List[dict],
        smokes: List[dict],
        mollies: List[dict],
        flashes: List[dict],
        recent_kills: List[dict],
        tick: int,
        round_num: int
    ) -> DeathAnalysis:
        """BRUTAL death analysis."""
        
        # Round reset
        if round_num != self.current_round:
            self.current_round = round_num
            self.round_deaths = []
            self.round_death_order = 0
            self.round_kills = []
        
        self.round_death_order += 1
        self.round_kills.extend(recent_kills)
        
        victim_name = kill_event.get('victim', '?')
        attacker_name = kill_event.get('attacker', '?')
        victim_team = kill_event.get('victim_team', 'CT')
        
        victim_pos = self._get_victim_position(kill_event, players, victim_name)
        
        # Find teammates and enemies
        teammates = [p for p in players if p.get('team') == victim_team 
                     and p.get('name') != victim_name and p.get('alive', False)]
        enemies = [p for p in players if p.get('team') != victim_team and p.get('alive', False)]
        
        teammate_distance = self._nearest_teammate_distance(victim_pos, teammates)
        enemy_count = len(enemies) + 1  # +1 for attacker
        teammate_count = len(teammates)
        
        mistakes = []
        reasons = []
        severity = 1
        
        # ===== BRUTAL ANALYSIS =====
        
        # 1. ISOLATED - No support anywhere
        if teammate_distance > self.ISOLATED_DISTANCE:
            mistakes.append(MistakeType.ISOLATED)
            reasons.append(f"ISOLATED: {int(teammate_distance)}u from team")
            severity = 5
        
        # 2. CROSSFIRE - Multiple angles
        if enemy_count >= 2:
            angles = self._count_enemy_angles(victim_pos, enemies)
            if angles >= 2:
                mistakes.append(MistakeType.CROSSFIRE)
                reasons.append(f"CROSSFIRE: {angles} angles exposed")
                severity = max(severity, 5)
        
        # 3. SOLO PUSH - Way ahead of team
        if teammate_distance > self.SOLO_PUSH_DISTANCE and teammate_count >= 2:
            mistakes.append(MistakeType.SOLO_PUSH)
            reasons.append(f"SOLO PUSH: {int(teammate_distance)}u ahead")
            severity = max(severity, 5)
        
        # 4. FLASHED - Blinded
        was_flashed = self._was_victim_flashed(victim_pos, flashes, tick)
        if was_flashed:
            mistakes.append(MistakeType.FLASHED)
            reasons.append("FLASHED: Killed while blind")
            severity = max(severity, 3)
        
        # 5. IN MOLLY - Dumb fire death
        in_utility = self._in_molotov(victim_pos, mollies, tick)
        if in_utility:
            mistakes.append(MistakeType.IN_MOLLY)
            reasons.append("IN FIRE: Died in molly")
            severity = max(severity, 3)
        
        # 6. TRADE CHECK
        was_traded = self._check_if_traded(attacker_name, recent_kills, tick)
        was_tradeable = teammate_distance < self.CLOSE_SUPPORT
        
        if was_traded:
            mistakes.append(MistakeType.TRADED)
            reasons.append("TRADED: Death got traded")
            severity = max(1, severity - 1)  # Reduce severity
        elif was_tradeable and teammate_count > 0:
            if MistakeType.ISOLATED not in mistakes:
                mistakes.append(MistakeType.NO_TRADE)
                reasons.append(f"NO TRADE: {int(teammate_distance)}u teammate didn't trade")
                severity = max(severity, 4)
        
        # 7. OUTNUMBERED
        if enemy_count > teammate_count + 2:
            if teammate_count == 0:
                mistakes.append(MistakeType.CLUTCH_ATTEMPT)
                reasons.append(f"CLUTCH: 1v{enemy_count}")
                severity = max(severity, 1)
            else:
                mistakes.append(MistakeType.OUTNUMBERED)
                reasons.append(f"OUTNUMBERED: {enemy_count}v{teammate_count + 1}")
                severity = max(severity, 3)
        
        # 8. FIRST CONTACT
        if self.round_death_order == 1 and not mistakes:
            mistakes.append(MistakeType.FIRST_CONTACT)
            reasons.append("ENTRY: First contact")
            severity = max(severity, 2)
        
        # 9. Fair duel fallback
        if not mistakes:
            mistakes.append(MistakeType.FAIR_DUEL)
            reasons.append("AIM DUEL: Lost fair fight")
            severity = 1
        
        analysis = DeathAnalysis(
            victim_name=victim_name,
            victim_team=victim_team,
            attacker_name=attacker_name,
            tick=tick,
            round_num=round_num,
            position=victim_pos,
            mistakes=mistakes,
            reasons=reasons,
            severity=severity,
            was_tradeable=was_tradeable,
            was_traded=was_traded,
            teammate_distance=teammate_distance,
            was_flashed=was_flashed,
            in_utility=in_utility,
            enemy_count=enemy_count,
            teammate_count=teammate_count,
        )
        
        self.death_history.append(analysis)
        self.round_deaths.append(analysis)
        
        # Update player stats
        self._update_player_stats(analysis)
        
        return analysis
    
    def _update_player_stats(self, analysis: DeathAnalysis):
        """Update player performance stats."""
        name = analysis.victim_name
        if name not in self.player_stats:
            self.player_stats[name] = PlayerStats(name=name, team=analysis.victim_team)
        
        stats = self.player_stats[name]
        stats.deaths += 1
        stats.total_blame += analysis.blame_score()
        stats.death_analyses.append(analysis)
        
        primary = analysis.primary_mistake()
        key = primary.value
        stats.mistake_counts[key] = stats.mistake_counts.get(key, 0) + 1
    
    def reset_round(self):
        """Reset round-specific tracking."""
        self.round_deaths = []
        self.round_death_order = 0
    
    def update_kill(self, attacker_name: str, team: str):
        """Record a kill for ranking."""
        if attacker_name not in self.player_stats:
            self.player_stats[attacker_name] = PlayerStats(name=attacker_name, team=team)
        self.player_stats[attacker_name].kills += 1
    
    def get_rankings(self) -> List[PlayerStats]:
        """Get players ranked by performance."""
        ranked = sorted(self.player_stats.values(), 
                       key=lambda p: -p.performance_score)
        return ranked
    
    def get_round_summary(self) -> dict:
        """Round summary statistics."""
        if not self.round_deaths:
            return {'total': 0, 'mistakes': {}, 'avg_severity': 0}
        
        mistake_counts = {}
        for death in self.round_deaths:
            primary = death.primary_mistake()
            key = primary.value
            mistake_counts[key] = mistake_counts.get(key, 0) + 1
        
        total_blame = sum(d.blame_score() for d in self.round_deaths)
        
        return {
            'total': len(self.round_deaths),
            'mistakes': mistake_counts,
            'avg_severity': sum(d.severity for d in self.round_deaths) / len(self.round_deaths),
            'total_blame': total_blame,
            'avg_blame': total_blame / len(self.round_deaths),
        }
    
    def _get_victim_position(self, kill_event: dict, players: List[dict], 
                             victim_name: str) -> Tuple[float, float]:
        if kill_event.get('victim_pos'):
            pos = kill_event['victim_pos']
            if hasattr(pos, 'x'):
                return (pos.x, pos.y)
        
        for p in players:
            if p.get('name') == victim_name:
                return (p.get('x', 0), p.get('y', 0))
        
        return (0, 0)
    
    def _nearest_teammate_distance(self, pos: Tuple[float, float], 
                                   teammates: List[dict]) -> float:
        if not teammates:
            return 9999
        
        min_dist = 9999
        for t in teammates:
            dx = pos[0] - t.get('x', 0)
            dy = pos[1] - t.get('y', 0)
            dist = math.sqrt(dx*dx + dy*dy)
            min_dist = min(min_dist, dist)
        
        return min_dist
    
    def _check_if_traded(self, attacker_name: str, recent_kills: List[dict], 
                         tick: int) -> bool:
        for k in recent_kills:
            if k.get('victim') == attacker_name:
                k_tick = k.get('tick', 0)
                if tick < k_tick <= tick + self.TRADE_WINDOW_TICKS:
                    return True
        return False
    
    def _was_victim_flashed(self, pos: Tuple[float, float], 
                            flashes: List[dict], tick: int) -> bool:
        for f in flashes:
            if f['start'] <= tick <= f['start'] + self.FLASH_EFFECT_TICKS:
                dx = pos[0] - f['x']
                dy = pos[1] - f['y']
                if math.sqrt(dx*dx + dy*dy) < 800:
                    return True
        return False
    
    def _in_molotov(self, pos: Tuple[float, float], mollies: List[dict], 
                    tick: int) -> bool:
        for m in mollies:
            if m['start'] <= tick <= m['end']:
                dx = pos[0] - m['x']
                dy = pos[1] - m['y']
                if math.sqrt(dx*dx + dy*dy) < 180:
                    return True
        return False
    
    def _count_enemy_angles(self, pos: Tuple[float, float], 
                            enemies: List[dict]) -> int:
        if len(enemies) < 2:
            return len(enemies)
        
        angles = set()
        for e in enemies:
            dx = e.get('x', 0) - pos[0]
            dy = e.get('y', 0) - pos[1]
            if dx == 0 and dy == 0:
                continue
            angle = math.atan2(dy, dx)
            sector = int((angle + math.pi) / (math.pi / 4)) % 8
            angles.add(sector)
        
        return len(angles)
    
    @staticmethod
    def get_mistake_label(mistake: MistakeType) -> str:
        labels = {
            MistakeType.ISOLATED: "ISOLATED",
            MistakeType.CROSSFIRE: "CROSSFIRE",
            MistakeType.SOLO_PUSH: "SOLO PUSH",
            MistakeType.NO_TRADE: "NO TRADE",
            MistakeType.WIDE_PEEK: "WIDE PEEK",
            MistakeType.UTILITY_DEATH: "UTIL DEATH",
            MistakeType.FLASHED: "FLASHED",
            MistakeType.IN_MOLLY: "IN FIRE",
            MistakeType.OUTNUMBERED: "OUTNUMBERED",
            MistakeType.REPEEKER: "REPEEK",
            MistakeType.FIRST_CONTACT: "ENTRY",
            MistakeType.BAD_TIMING: "BAD TIMING",
            MistakeType.CLUTCH_ATTEMPT: "CLUTCH",
            MistakeType.TRADED: "TRADED",
            MistakeType.FAIR_DUEL: "AIM DUEL",
        }
        return labels.get(mistake, mistake.value.upper())
    
    @staticmethod
    def get_mistake_color(mistake: MistakeType) -> Tuple[int, int, int]:
        colors = {
            # Critical - Red
            MistakeType.ISOLATED: (255, 50, 50),
            MistakeType.CROSSFIRE: (255, 30, 30),
            MistakeType.SOLO_PUSH: (255, 60, 60),
            # Severe - Orange
            MistakeType.NO_TRADE: (255, 140, 40),
            MistakeType.WIDE_PEEK: (255, 160, 60),
            MistakeType.UTILITY_DEATH: (255, 120, 30),
            # Moderate - Yellow
            MistakeType.FLASHED: (255, 230, 80),
            MistakeType.IN_MOLLY: (255, 180, 50),
            MistakeType.OUTNUMBERED: (255, 200, 100),
            MistakeType.REPEEKER: (255, 210, 80),
            # Minor - Blue
            MistakeType.FIRST_CONTACT: (100, 160, 255),
            MistakeType.BAD_TIMING: (120, 180, 255),
            # Neutral - Gray/Green
            MistakeType.CLUTCH_ATTEMPT: (100, 200, 255),
            MistakeType.TRADED: (80, 200, 120),
            MistakeType.FAIR_DUEL: (150, 150, 150),
        }
        return colors.get(mistake, (200, 200, 200))
    
    def get_llm_prompt(self, analysis: DeathAnalysis) -> str:
        """Construct a context-rich prompt for the local LLM."""
        
        mistake = analysis.primary_mistake()
        mistake_label = self.get_mistake_label(mistake)
        
        context = f"""
        Player: {analysis.victim_name} ({analysis.victim_team})
        Map Situation:
        - Died to: {analysis.attacker_name}
        - Primary Error: {mistake_label} (Severity: {analysis.severity}/5)
        - Teammate Support: {int(analysis.teammate_distance)} units away ({analysis.teammate_count} nearby)
        - Enemies: Faced {analysis.enemy_count} opponents
        - Traded: {"Yes" if analysis.was_traded else "No"}
        - Flashed: {"Yes" if analysis.was_flashed else "No"}
        
        Detailed Context:
        The player made a {mistake_label} error.
        {' '.join(analysis.reasons)}
        
        Task:
        Coach {analysis.victim_name} directly. You MUST start your response by addressing them by name (e.g., "{analysis.victim_name}, you...").
        Explain clearly what they did wrong ({mistake_label}) and how to fix it next round of this CS2 match.
        Keep it sharp, tactical, and under 40 words.
        """
        return context
    
    def get_player_analysis_prompt(self, player_stats: PlayerStats) -> str:
        """Construct a deep analytical review prompt for a specific player."""
        
        # Identify top mistakes
        mistakes = sorted(player_stats.mistake_counts.items(), key=lambda x: -x[1])
        top_mistakes = [f"{m[0].upper()} ({c}x)" for m, c in mistakes[:3]]
        
        # Find worst death (highest severity)
        worst_death = None
        if player_stats.death_analyses:
            worst_death = max(player_stats.death_analyses, key=lambda d: d.severity)
            
        context = f"""
        Player: {player_stats.name} ({player_stats.team})
        Overall Performance:
        - Grade: {player_stats.rank_grade} (Score: {player_stats.performance_score:.1f})
        - K/D: {player_stats.kills}/{player_stats.deaths}
        - Tactical Discipline (Blame): {player_stats.avg_blame:.0f}% (Lower is better)
        
        Recurring Issues:
        {', '.join(top_mistakes) if top_mistakes else "None detected yet."}
        
        Worst Mistake Example:
        {f"Died to {worst_death.attacker_name} due to {self.get_mistake_label(worst_death.primary_mistake())}" if worst_death else "N/A"}
        
        Task:
        Provide a professional tactical analysis for {player_stats.name}.
        1. Address them by name.
        2. Analyze their biggest weakness based on the recurring mistakes.
        3. Give 2 specific, high-level improvements to raise their Grade.
        4. Be brutally honest but constructive. Max 50 words.
        """
        return context

    
    @staticmethod
    def get_grade_color(grade: str) -> Tuple[int, int, int]:
        colors = {
            'S': (255, 215, 0),    # Gold
            'A': (100, 255, 100),  # Green
            'B': (100, 200, 255),  # Blue
            'C': (255, 255, 100),  # Yellow
            'D': (255, 150, 100),  # Orange
            'F': (255, 80, 80),    # Red
        }
        return colors.get(grade, (150, 150, 150))

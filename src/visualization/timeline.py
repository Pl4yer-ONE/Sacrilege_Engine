"""Timeline replay system."""

from dataclasses import dataclass, field
from typing import Optional
import json

from src.models import DemoData, RoundData, KillEvent, Team, Vector3


@dataclass
class TimelineEvent:
    """A single event on the timeline."""
    tick: int
    time_seconds: float
    round_number: int
    
    event_type: str  # kill, death, flash, smoke, bomb_plant, bomb_defuse, round_start, round_end
    
    # Actor info
    actor_id: str = ""
    actor_name: str = ""
    actor_team: str = ""
    
    # Target info (for kills)
    target_id: str = ""
    target_name: str = ""
    target_team: str = ""
    
    # Details
    weapon: str = ""
    headshot: bool = False
    through_smoke: bool = False
    
    # Position
    position: Optional[tuple[float, float, float]] = None
    
    # Impact score (how important was this event)
    impact_score: float = 0.0


@dataclass
class RoundTimeline:
    """Timeline for a single round."""
    round_number: int
    start_tick: int
    end_tick: int
    winner: Optional[str] = None
    
    events: list[TimelineEvent] = field(default_factory=list)
    
    # Summary stats
    ct_kills: int = 0
    t_kills: int = 0
    duration_seconds: float = 0.0


@dataclass 
class MatchTimeline:
    """Complete match timeline."""
    map_name: str
    demo_hash: str
    tick_rate: float
    
    rounds: list[RoundTimeline] = field(default_factory=list)
    
    # Match summary
    ct_score: int = 0
    t_score: int = 0
    total_kills: int = 0


class TimelineGenerator:
    """
    Generates timeline data for match replay.
    
    Creates chronological event sequence for:
    - Kill feed
    - Utility usage
    - Bomb events
    - Round outcomes
    
    Output: JSON for timeline visualization
    """
    
    def __init__(self, tick_rate: float = 64.0):
        self.tick_rate = tick_rate
    
    def generate(self, demo_data: DemoData) -> MatchTimeline:
        """Generate complete match timeline."""
        timeline = MatchTimeline(
            map_name=demo_data.header.map_name,
            demo_hash="",
            tick_rate=demo_data.header.tick_rate or 64.0,
        )
        
        self.tick_rate = timeline.tick_rate
        
        ct_score = 0
        t_score = 0
        
        for round_data in demo_data.rounds:
            round_timeline = self._process_round(round_data, demo_data)
            timeline.rounds.append(round_timeline)
            
            # Update scores
            if round_data.winner == Team.CT:
                ct_score += 1
            elif round_data.winner == Team.T:
                t_score += 1
            
            timeline.total_kills += len(round_data.kills)
        
        timeline.ct_score = ct_score
        timeline.t_score = t_score
        
        return timeline
    
    def _process_round(self, round_data: RoundData, demo_data: DemoData) -> RoundTimeline:
        """Process a single round into timeline."""
        round_tl = RoundTimeline(
            round_number=round_data.round_number,
            start_tick=round_data.start_tick,
            end_tick=round_data.end_tick,
            winner=round_data.winner.name if round_data.winner else None,
            duration_seconds=(round_data.end_tick - round_data.start_tick) / self.tick_rate,
        )
        
        # Process kills
        for kill in round_data.kills:
            attacker = demo_data.players.get(kill.attacker_id)
            victim = demo_data.players.get(kill.victim_id)
            
            event = TimelineEvent(
                tick=kill.tick,
                time_seconds=(kill.tick - round_data.start_tick) / self.tick_rate,
                round_number=round_data.round_number,
                event_type="kill",
                actor_id=kill.attacker_id,
                actor_name=attacker.name if attacker else "Unknown",
                actor_team=attacker.team.name if attacker else "",
                target_id=kill.victim_id,
                target_name=victim.name if victim else "Unknown",
                target_team=victim.team.name if victim else "",
                weapon=kill.weapon,
                headshot=kill.headshot,
                through_smoke=kill.through_smoke,
                position=(kill.attacker_position.x, kill.attacker_position.y, kill.attacker_position.z) if kill.attacker_position else None,
                impact_score=self._calculate_kill_impact(kill, round_data),
            )
            
            round_tl.events.append(event)
            
            # Count kills per team
            if attacker and attacker.team == Team.CT:
                round_tl.ct_kills += 1
            elif attacker and attacker.team == Team.T:
                round_tl.t_kills += 1
        
        # Sort events by tick
        round_tl.events.sort(key=lambda e: e.tick)
        
        return round_tl
    
    def _calculate_kill_impact(self, kill: KillEvent, round_data: RoundData) -> float:
        """Calculate impact score for a kill (0-100)."""
        impact = 50.0
        
        # First blood bonus
        if round_data.kills and round_data.kills[0].tick == kill.tick:
            impact += 20
        
        # Headshot bonus
        if kill.headshot:
            impact += 10
        
        # Through smoke bonus
        if kill.through_smoke:
            impact += 15
        
        return min(100, impact)
    
    def to_json(self, timeline: MatchTimeline) -> str:
        """Export timeline as JSON."""
        data = {
            "map": timeline.map_name,
            "tick_rate": timeline.tick_rate,
            "score": {"ct": timeline.ct_score, "t": timeline.t_score},
            "total_kills": timeline.total_kills,
            "rounds": []
        }
        
        for r in timeline.rounds:
            round_data = {
                "number": r.round_number,
                "winner": r.winner,
                "duration": r.duration_seconds,
                "ct_kills": r.ct_kills,
                "t_kills": r.t_kills,
                "events": []
            }
            
            for e in r.events:
                round_data["events"].append({
                    "time": e.time_seconds,
                    "type": e.event_type,
                    "actor": e.actor_name,
                    "actor_team": e.actor_team,
                    "target": e.target_name,
                    "target_team": e.target_team,
                    "weapon": e.weapon,
                    "headshot": e.headshot,
                    "impact": e.impact_score,
                })
            
            data["rounds"].append(round_data)
        
        return json.dumps(data, indent=2)
    
    def generate_kill_feed(self, timeline: MatchTimeline, round_number: int) -> list[str]:
        """Generate kill feed strings for a round."""
        feed = []
        
        for r in timeline.rounds:
            if r.round_number == round_number:
                for e in r.events:
                    if e.event_type == "kill":
                        hs = " (HS)" if e.headshot else ""
                        smoke = " ⦿" if e.through_smoke else ""
                        feed.append(
                            f"[{e.time_seconds:.1f}s] {e.actor_name} ⟶ {e.target_name} [{e.weapon}]{hs}{smoke}"
                        )
                break
        
        return feed

"""Team synergy web visualization."""

from dataclasses import dataclass, field
from typing import Optional
import json

from src.models import DemoData, RoundData, Team


@dataclass
class PlayerConnection:
    """Connection between two players."""
    player1_id: str
    player2_id: str
    
    # Synergy metrics
    trades_given: int = 0  # P1 traded P2's death
    trades_received: int = 0  # P2 traded P1's death
    flash_assists: int = 0  # P1 flashed for P2's kill
    
    # Distance metrics
    avg_distance: float = 0.0  # Average distance when one dies
    
    # Combo kills (both got kills within 3s)
    combo_rounds: int = 0
    
    @property
    def synergy_score(self) -> float:
        """Calculate overall synergy (0-100)."""
        score = 0.0
        score += (self.trades_given + self.trades_received) * 10
        score += self.flash_assists * 15
        score += self.combo_rounds * 5
        score -= max(0, (self.avg_distance - 500)) / 50  # Penalty for distance
        return max(0, min(100, score))


@dataclass
class TeamWeb:
    """Team synergy web for all players."""
    team: str
    map_name: str
    
    players: dict[str, str] = field(default_factory=dict)  # id -> name
    connections: list[PlayerConnection] = field(default_factory=list)
    
    # Team-level metrics
    avg_synergy: float = 0.0
    best_pair: tuple[str, str] = ("", "")
    worst_pair: tuple[str, str] = ("", "")


class TeamSynergyGenerator:
    """
    Generates team synergy visualization data.
    
    Measures:
    - Trade success between pairs
    - Flash assist frequency
    - Positioning cohesion
    - Combo effectiveness
    
    Output: JSON for web graph (D3.js compatible)
    """
    
    TRADE_WINDOW_TICKS = 3 * 64  # 3 seconds at 64 tick
    
    def generate(self, demo_data: DemoData, team: Team) -> TeamWeb:
        """Generate synergy web for a team."""
        # Get team players
        team_players = {
            pid: info for pid, info in demo_data.players.items()
            if info.team == team
        }
        
        web = TeamWeb(
            team=team.name,
            map_name=demo_data.header.map_name,
            players={pid: info.name for pid, info in team_players.items()},
        )
        
        # Create connections between all pairs
        player_ids = list(team_players.keys())
        for i, p1 in enumerate(player_ids):
            for p2 in player_ids[i+1:]:
                conn = self._calculate_connection(demo_data, p1, p2, team)
                web.connections.append(conn)
        
        # Calculate team averages
        if web.connections:
            web.avg_synergy = sum(c.synergy_score for c in web.connections) / len(web.connections)
            
            # Find best/worst pairs
            best = max(web.connections, key=lambda c: c.synergy_score)
            worst = min(web.connections, key=lambda c: c.synergy_score)
            
            web.best_pair = (
                web.players.get(best.player1_id, ""),
                web.players.get(best.player2_id, ""),
            )
            web.worst_pair = (
                web.players.get(worst.player1_id, ""),
                web.players.get(worst.player2_id, ""),
            )
        
        return web
    
    def _calculate_connection(
        self,
        demo_data: DemoData,
        p1: str,
        p2: str,
        team: Team
    ) -> PlayerConnection:
        """Calculate synergy between two players."""
        conn = PlayerConnection(player1_id=p1, player2_id=p2)
        
        for round_data in demo_data.rounds:
            # Check for trades
            p1_death_tick = None
            p2_death_tick = None
            p1_kills = []
            p2_kills = []
            
            for kill in round_data.kills:
                # Track deaths
                if kill.victim_id == p1:
                    p1_death_tick = kill.tick
                if kill.victim_id == p2:
                    p2_death_tick = kill.tick
                
                # Track kills
                if kill.attacker_id == p1:
                    p1_kills.append(kill.tick)
                if kill.attacker_id == p2:
                    p2_kills.append(kill.tick)
            
            # Check if P2 traded P1's death
            if p1_death_tick:
                for kill_tick in p2_kills:
                    if 0 < kill_tick - p1_death_tick < self.TRADE_WINDOW_TICKS:
                        conn.trades_given += 1
                        break
            
            # Check if P1 traded P2's death
            if p2_death_tick:
                for kill_tick in p1_kills:
                    if 0 < kill_tick - p2_death_tick < self.TRADE_WINDOW_TICKS:
                        conn.trades_received += 1
                        break
            
            # Check for combo kills (both got kills in same round)
            if p1_kills and p2_kills:
                for t1 in p1_kills:
                    for t2 in p2_kills:
                        if abs(t1 - t2) < self.TRADE_WINDOW_TICKS:
                            conn.combo_rounds += 1
                            break
                    else:
                        continue
                    break
        
        return conn
    
    def to_json(self, web: TeamWeb) -> str:
        """Export team web as JSON (D3.js force-directed compatible)."""
        data = {
            "team": web.team,
            "map": web.map_name,
            "avg_synergy": web.avg_synergy,
            "best_pair": web.best_pair,
            "worst_pair": web.worst_pair,
            "nodes": [
                {"id": pid, "name": name}
                for pid, name in web.players.items()
            ],
            "links": [
                {
                    "source": c.player1_id,
                    "target": c.player2_id,
                    "strength": c.synergy_score,
                    "trades": c.trades_given + c.trades_received,
                    "combos": c.combo_rounds,
                }
                for c in web.connections
            ],
        }
        return json.dumps(data, indent=2)
    
    def to_text_summary(self, web: TeamWeb) -> str:
        """Generate text summary of team synergy."""
        lines = [
            f"=== Team Synergy: {web.team} ===",
            f"Map: {web.map_name}",
            f"",
            f"Average synergy: {web.avg_synergy:.1f}/100",
            f"Best duo: {web.best_pair[0]} + {web.best_pair[1]}",
            f"Needs work: {web.worst_pair[0]} + {web.worst_pair[1]}",
            f"",
            "Player connections:",
        ]
        
        for conn in sorted(web.connections, key=lambda c: c.synergy_score, reverse=True):
            p1_name = web.players.get(conn.player1_id, "?")
            p2_name = web.players.get(conn.player2_id, "?")
            lines.append(
                f"  {p1_name} ↔ {p2_name}: {conn.synergy_score:.0f} "
                f"(trades: {conn.trades_given + conn.trades_received}, combos: {conn.combo_rounds})"
            )
        
        return "\n".join(lines)

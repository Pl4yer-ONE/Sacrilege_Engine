"""Player state tracking from demo ticks."""

from typing import Optional
import pandas as pd

from demoparser2 import DemoParser

from src.models import PlayerState, PlayerInfo, Vector3, ViewAngles, Team
from src.config import get_settings


class PlayerTracker:
    """Tracks player state throughout demo."""
    
    # Fields to extract from ticks
    TICK_FIELDS = [
        "tick", "steamid", "name", "team_num",
        "X", "Y", "Z",
        "velocity_X", "velocity_Y", "velocity_Z",
        "pitch", "yaw",
        "health", "armor_value", "has_helmet", "has_defuser",
        "active_weapon_name", "current_equip_value", "cash_spent_this_round",
        "is_alive", "flash_duration",
    ]
    
    def __init__(self, parser: DemoParser):
        self.parser = parser
        self.settings = get_settings()
        self.sample_rate = self.settings.tick_sample_rate
    
    def get_player_info(self) -> dict[str, PlayerInfo]:
        """Extract player information from demo."""
        players: dict[str, PlayerInfo] = {}
        
        try:
            # Get player info from ticks
            df = self.parser.parse_ticks(["steamid", "name", "team_num"])
            
            # Group by steamid and get unique players
            for steam_id in df['steamid'].unique():
                player_df = df[df['steamid'] == steam_id]
                if len(player_df) == 0:
                    continue
                
                first_row = player_df.iloc[0]
                team_num = int(first_row.get('team_num', 0))
                
                players[str(steam_id)] = PlayerInfo(
                    steam_id=str(steam_id),
                    name=str(first_row.get('name', 'Unknown')),
                    team=self._team_from_num(team_num),
                )
        except Exception:
            pass
        
        return players
    
    def get_sampled_states(self) -> list[PlayerState]:
        """Get sampled player states (every N ticks)."""
        states: list[PlayerState] = []
        
        try:
            df = self.parser.parse_ticks(self.TICK_FIELDS)
            
            # Sample every N ticks
            ticks = df['tick'].unique()
            sampled_ticks = [t for i, t in enumerate(ticks) if i % self.sample_rate == 0]
            
            sampled_df = df[df['tick'].isin(sampled_ticks)]
            
            for _, row in sampled_df.iterrows():
                state = self._row_to_state(row)
                if state:
                    states.append(state)
        except Exception:
            pass
        
        return states
    
    def get_states_at_tick(self, tick: int) -> dict[str, PlayerState]:
        """Get all player states at a specific tick."""
        states: dict[str, PlayerState] = {}
        
        try:
            df = self.parser.parse_ticks(self.TICK_FIELDS)
            tick_df = df[df['tick'] == tick]
            
            for _, row in tick_df.iterrows():
                state = self._row_to_state(row)
                if state:
                    states[state.steam_id] = state
        except Exception:
            pass
        
        return states
    
    def get_states_in_range(self, start_tick: int, end_tick: int) -> dict[int, dict[str, PlayerState]]:
        """Get player states for a tick range (sampled)."""
        result: dict[int, dict[str, PlayerState]] = {}
        
        try:
            df = self.parser.parse_ticks(self.TICK_FIELDS)
            
            # Filter to range
            range_df = df[(df['tick'] >= start_tick) & (df['tick'] <= end_tick)]
            
            # Sample
            ticks = sorted(range_df['tick'].unique())
            sampled_ticks = [t for i, t in enumerate(ticks) if i % self.sample_rate == 0]
            
            for tick in sampled_ticks:
                tick_df = range_df[range_df['tick'] == tick]
                states: dict[str, PlayerState] = {}
                
                for _, row in tick_df.iterrows():
                    state = self._row_to_state(row)
                    if state:
                        states[state.steam_id] = state
                
                result[tick] = states
        except Exception:
            pass
        
        return result
    
    def _row_to_state(self, row: pd.Series) -> Optional[PlayerState]:
        """Convert DataFrame row to PlayerState."""
        try:
            steam_id = str(row.get('steamid', ''))
            if not steam_id:
                return None
            
            team_num = int(row.get('team_num', 0))
            
            return PlayerState(
                tick=int(row.get('tick', 0)),
                steam_id=steam_id,
                name=str(row.get('name', 'Unknown')),
                team=self._team_from_num(team_num),
                position=Vector3(
                    float(row.get('X', 0)),
                    float(row.get('Y', 0)),
                    float(row.get('Z', 0))
                ),
                velocity=Vector3(
                    float(row.get('velocity_X', 0)),
                    float(row.get('velocity_Y', 0)),
                    float(row.get('velocity_Z', 0))
                ),
                view_angles=ViewAngles(
                    float(row.get('pitch', 0)),
                    float(row.get('yaw', 0))
                ),
                health=int(row.get('health', 0)),
                armor=int(row.get('armor_value', 0)),
                has_helmet=bool(row.get('has_helmet', False)),
                has_defuser=bool(row.get('has_defuser', False)),
                is_alive=bool(row.get('is_alive', True)),
                is_flashed=float(row.get('flash_duration', 0)) > 0,
                flash_duration=float(row.get('flash_duration', 0)),
                active_weapon=str(row.get('active_weapon_name', '')),
                equipment_value=int(row.get('current_equip_value', 0)),
            )
        except Exception:
            return None
    
    def _team_from_num(self, team_num: int) -> Team:
        """Convert team number to Team enum."""
        if team_num == 2:
            return Team.T
        elif team_num == 3:
            return Team.CT
        return Team.SPEC

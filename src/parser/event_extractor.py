"""Event extraction from CS2 demos."""

from typing import Iterator, Any
import pandas as pd

from demoparser2 import DemoParser

from src.models import (
    GameEvent, KillEvent, ShotEvent, FlashEvent, SmokeEvent,
    UtilityEvent, EventType, Vector3, ViewAngles, Team
)


def _to_dataframe(data: Any) -> pd.DataFrame:
    """Convert demoparser2 output to DataFrame."""
    if isinstance(data, pd.DataFrame):
        return data
    if isinstance(data, list):
        if len(data) == 0:
            return pd.DataFrame()
        return pd.DataFrame(data)
    return pd.DataFrame()


def _safe_get(row, key, default=None):
    """Safely get value from row (works for dict and Series)."""
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        if key in row.index:
            return row[key]
    except:
        pass
    return default


class EventExtractor:
    """Extracts game events from parsed demo data."""
    
    # Event name mapping from demoparser2 to internal types
    EVENT_MAP = {
        'weapon_fire': EventType.SHOT,
        'player_death': EventType.KILL,
        'flashbang_detonate': EventType.FLASH,
        'smokegrenade_detonate': EventType.SMOKE,
        'inferno_startburn': EventType.MOLOTOV,
        'hegrenade_detonate': EventType.HE_GRENADE,
        'bomb_planted': EventType.BOMB_PLANT,
        'bomb_defused': EventType.BOMB_DEFUSE,
        'bomb_exploded': EventType.BOMB_EXPLODE,
        'round_start': EventType.ROUND_START,
        'round_end': EventType.ROUND_END,
    }
    
    def __init__(self, parser: DemoParser):
        self.parser = parser
    
    def extract_all(self) -> list[GameEvent]:
        """Extract all relevant events from demo."""
        events: list[GameEvent] = []
        
        # Extract kills
        events.extend(self.extract_kills())
        
        # Extract shots (skip for now - too many events)
        # events.extend(self.extract_shots())
        
        # Extract utility
        events.extend(self.extract_flashes())
        events.extend(self.extract_smokes())
        
        # Sort by tick
        events.sort(key=lambda e: e.tick)
        
        return events
    
    def extract_kills(self) -> list[KillEvent]:
        """Extract all kill events with full context."""
        try:
            data = self.parser.parse_event("player_death")
            df = _to_dataframe(data)
        except Exception as e:
            print(f"Error extracting kills: {e}")
            return []
        
        if df.empty:
            return []
        
        # Try to get position data from tick parsing (only for kill ticks)
        position_cache = {}
        try:
            # Get unique ticks from kills
            kill_ticks = df['tick'].unique().tolist() if 'tick' in df.columns else []
            
            if kill_ticks:
                tick_data = self.parser.parse_ticks(["X", "Y", "Z"], ticks=kill_ticks)
                tick_df = _to_dataframe(tick_data)
                if not tick_df.empty:
                    # Create lookup: (tick, steamid) -> (x, y, z)
                    for _, row in tick_df.iterrows():
                        key = (int(_safe_get(row, 'tick', 0)), str(_safe_get(row, 'steamid', '')))
                        position_cache[key] = (
                            float(_safe_get(row, 'X', 0)),
                            float(_safe_get(row, 'Y', 0)),
                            float(_safe_get(row, 'Z', 0)),
                        )
        except Exception as e:
            pass  # Position data optional
        
        kills = []
        for _, row in df.iterrows():
            try:
                tick = int(_safe_get(row, 'tick', 0))
                attacker_steamid = str(_safe_get(row, 'attacker_steamid', ''))
                victim_steamid = str(_safe_get(row, 'user_steamid', ''))
                
                # Look up positions
                attacker_pos = None
                victim_pos = None
                
                if (tick, attacker_steamid) in position_cache:
                    x, y, z = position_cache[(tick, attacker_steamid)]
                    attacker_pos = Vector3(x, y, z)
                
                if (tick, victim_steamid) in position_cache:
                    x, y, z = position_cache[(tick, victim_steamid)]
                    victim_pos = Vector3(x, y, z)
                
                kills.append(KillEvent(
                    tick=tick,
                    event_type=EventType.KILL,
                    attacker_id=attacker_steamid,
                    victim_id=victim_steamid,
                    attacker_position=attacker_pos,
                    victim_position=victim_pos,
                    weapon=str(_safe_get(row, 'weapon', '')),
                    headshot=bool(_safe_get(row, 'headshot', False)),
                    penetrated=bool(_safe_get(row, 'penetrated', False)),
                    noscope=bool(_safe_get(row, 'noscope', False)),
                    through_smoke=bool(_safe_get(row, 'thrusmoke', False)),
                ))
            except Exception as e:
                continue
        
        return kills
    
    def extract_shots(self) -> list[ShotEvent]:
        """Extract weapon fire events."""
        try:
            data = self.parser.parse_event("weapon_fire")
            df = _to_dataframe(data)
        except Exception:
            return []
        
        if df.empty:
            return []
        
        shots = []
        for _, row in df.iterrows():
            try:
                shots.append(ShotEvent(
                    tick=int(_safe_get(row, 'tick', 0)),
                    event_type=EventType.SHOT,
                    player_id=str(_safe_get(row, 'user_steamid', '')),
                    weapon=str(_safe_get(row, 'weapon', '')),
                ))
            except Exception:
                continue
        
        return shots
    
    def extract_flashes(self) -> list[FlashEvent]:
        """Extract flashbang events."""
        try:
            data = self.parser.parse_event("flashbang_detonate")
            df = _to_dataframe(data)
        except Exception:
            return []
        
        if df.empty:
            return []
        
        flashes = []
        for _, row in df.iterrows():
            try:
                flashes.append(FlashEvent(
                    tick=int(_safe_get(row, 'tick', 0)),
                    event_type=EventType.FLASH,
                    thrower_id=str(_safe_get(row, 'user_steamid', '')),
                ))
            except Exception:
                continue
        
        # Try to correlate with player_blind events for effectiveness
        self._correlate_flash_blinds(flashes)
        
        return flashes
    
    def _correlate_flash_blinds(self, flashes: list[FlashEvent]) -> None:
        """Correlate flash events with blind effects."""
        if not flashes:
            return
            
        try:
            data = self.parser.parse_event("player_blind")
            blinds_df = _to_dataframe(data)
        except Exception:
            return
        
        if blinds_df.empty:
            return
        
        # Group blinds by approximate tick range
        for flash in flashes:
            tick_range = range(flash.tick, flash.tick + 10)
            
            enemies = 0
            teammates = 0
            total_duration = 0.0
            count = 0
            
            for _, blind in blinds_df.iterrows():
                try:
                    blind_tick = int(_safe_get(blind, 'tick', 0))
                    if blind_tick in tick_range:
                        duration = float(_safe_get(blind, 'blind_duration', 0))
                        total_duration += duration
                        count += 1
                        
                        # Check if enemy or teammate
                        blind_team = _safe_get(blind, 'user_team_num', 0)
                        attacker_team = _safe_get(blind, 'attacker_team_num', 0)
                        
                        if blind_team != attacker_team:
                            enemies += 1
                        else:
                            if str(_safe_get(blind, 'user_steamid', '')) == flash.thrower_id:
                                flash.self_flash = True
                            else:
                                teammates += 1
                except Exception:
                    continue
            
            flash.enemies_blinded = enemies
            flash.teammates_blinded = teammates
            flash.avg_blind_duration = total_duration / count if count > 0 else 0.0
    
    def extract_smokes(self) -> list[SmokeEvent]:
        """Extract smoke grenade events."""
        try:
            data = self.parser.parse_event("smokegrenade_detonate")
            df = _to_dataframe(data)
        except Exception:
            return []
        
        if df.empty:
            return []
        
        smokes = []
        for _, row in df.iterrows():
            try:
                tick = int(_safe_get(row, 'tick', 0))
                smokes.append(SmokeEvent(
                    tick=tick,
                    event_type=EventType.SMOKE,
                    thrower_id=str(_safe_get(row, 'user_steamid', '')),
                    start_tick=tick,
                    end_tick=tick + 18 * 64,  # ~18 seconds at 64 tick
                ))
            except Exception:
                continue
        
        return smokes
    
    def extract_round_events(self) -> tuple[list[int], list[int]]:
        """Extract round start and end ticks."""
        starts = []
        ends = []
        
        try:
            data = self.parser.parse_event("round_start")
            df = _to_dataframe(data)
            for _, row in df.iterrows():
                starts.append(int(_safe_get(row, 'tick', 0)))
        except Exception:
            pass
        
        try:
            data = self.parser.parse_event("round_end")
            df = _to_dataframe(data)
            for _, row in df.iterrows():
                ends.append(int(_safe_get(row, 'tick', 0)))
        except Exception:
            pass
        
        return sorted(starts), sorted(ends)

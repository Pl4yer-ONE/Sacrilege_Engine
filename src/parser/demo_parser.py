"""Main demo parser orchestrator."""

from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from demoparser2 import DemoParser as DP2Parser

from src.models import (
    DemoData, DemoHeader, RoundData, PlayerInfo, GameEvent, 
    KillEvent, Team
)
from src.parser.validator import DemoValidator, ValidationResult
from src.parser.event_extractor import EventExtractor
from src.parser.player_tracker import PlayerTracker


@dataclass
class ParseResult:
    """Result of demo parsing."""
    success: bool
    data: Optional[DemoData] = None
    error: Optional[str] = None
    file_hash: Optional[str] = None


class DemoParser:
    """Main demo parser that orchestrates all parsing stages."""
    
    def __init__(self):
        self.validator = DemoValidator()
    
    def parse(self, file_path: Path) -> ParseResult:
        """
        Parse a demo file through all stages.
        
        Stages:
        1. Validate demo file
        2. Extract events
        3. Track players
        4. Build round structure
        5. Return complete DemoData
        """
        # Stage 1: Validate
        validation = self.validator.validate(file_path)
        if not validation.valid:
            return ParseResult(success=False, error=validation.error)
        
        header = validation.header
        file_hash = validation.file_hash
        
        # Create demoparser2 instance
        try:
            parser = DP2Parser(str(file_path))
        except Exception as e:
            return ParseResult(success=False, error=f"Failed to open demo: {e}")
        
        # Stage 2: Extract events
        event_extractor = EventExtractor(parser)
        events = event_extractor.extract_all()
        
        # Stage 3: Track players
        player_tracker = PlayerTracker(parser)
        players = player_tracker.get_player_info()
        
        # Update player stats from kills
        self._aggregate_player_stats(players, events)
        
        # Stage 4: Build rounds
        round_starts, round_ends = event_extractor.extract_round_events()
        rounds = self._build_rounds(round_starts, round_ends, events)
        
        # Build final data
        demo_data = DemoData(
            header=header,
            players=players,
            rounds=rounds,
            events=events,
        )
        
        return ParseResult(
            success=True,
            data=demo_data,
            file_hash=file_hash
        )
    
    def _aggregate_player_stats(
        self, 
        players: dict[str, PlayerInfo], 
        events: list[GameEvent]
    ) -> None:
        """Aggregate player statistics from events."""
        for event in events:
            if isinstance(event, KillEvent):
                # Attacker gets kill
                if event.attacker_id in players:
                    players[event.attacker_id].kills += 1
                    if event.headshot:
                        players[event.attacker_id].headshot_kills += 1
                
                # Victim gets death
                if event.victim_id in players:
                    players[event.victim_id].deaths += 1
    
    def _build_rounds(
        self,
        starts: list[int],
        ends: list[int],
        events: list[GameEvent]
    ) -> list[RoundData]:
        """Build round data from start/end ticks and events."""
        rounds: list[RoundData] = []
        
        # Pair starts with ends
        for i, start in enumerate(starts):
            end = ends[i] if i < len(ends) else starts[i + 1] if i + 1 < len(starts) else start + 10000
            
            # Get events for this round
            round_events = [e for e in events if start <= e.tick <= end]
            round_kills = [e for e in round_events if isinstance(e, KillEvent)]
            
            round_data = RoundData(
                round_number=i + 1,
                start_tick=start,
                end_tick=end,
                events=round_events,
                kills=round_kills,
            )
            
            rounds.append(round_data)
        
        return rounds
    
    def parse_quick(self, file_path: Path) -> tuple[Optional[DemoHeader], Optional[str]]:
        """Quick parse to get just header and hash."""
        validation = self.validator.validate(file_path)
        if not validation.valid:
            return None, validation.error
        return validation.header, None

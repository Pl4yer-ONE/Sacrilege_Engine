# SPDX-FileCopyrightText: 2026 Pl4yer-ONE <mahadevan.rajeev27@gmail.com>
# SPDX-License-Identifier: LicenseRef-Sacrilege-EULA

"""Unit tests for EventExtractor logic."""

import pytest
import sys
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser.event_extractor import EventExtractor
from src.models import EventType, Vector3

@pytest.fixture
def mock_parser():
    """Create a mock demoparser2 object."""
    return MagicMock()

class TestEventExtractor:
    """Test EventExtractor logic."""

    def test_extract_kills_with_positions(self, mock_parser):
        """Test kill extraction with position lookup."""
        extractor = EventExtractor(mock_parser)

        # Mock kill data
        kills_df = pd.DataFrame([{
            'tick': 1000,
            'attacker_steamid': '76561198000000001',
            'user_steamid': '76561198000000002',
            'weapon': 'ak47',
            'headshot': True,
            'penetrated': False,
            'noscope': False,
            'thrusmoke': False
        }])

        # Mock position data
        positions_df = pd.DataFrame([
            {'tick': 1000, 'steamid': '76561198000000001', 'X': 100, 'Y': 200, 'Z': 0},
            {'tick': 1000, 'steamid': '76561198000000002', 'X': 500, 'Y': 600, 'Z': 0},
        ])

        # Setup mock returns
        def parse_event_side_effect(event_name):
            if event_name == "player_death":
                return kills_df
            return pd.DataFrame()

        mock_parser.parse_event.side_effect = parse_event_side_effect
        mock_parser.parse_ticks.return_value = positions_df

        kills = extractor.extract_kills()

        assert len(kills) == 1
        kill = kills[0]
        assert kill.event_type == EventType.KILL
        assert kill.attacker_id == '76561198000000001'
        assert kill.headshot is True

        # Check positions
        assert kill.attacker_position is not None
        assert kill.attacker_position.x == 100
        assert kill.victim_position is not None
        assert kill.victim_position.x == 500

    def test_extract_kills_missing_positions(self, mock_parser):
        """Test kill extraction when position data is missing."""
        extractor = EventExtractor(mock_parser)

        kills_df = pd.DataFrame([{
            'tick': 1000,
            'attacker_steamid': '1',
            'user_steamid': '2',
        }])

        mock_parser.parse_event.return_value = kills_df
        mock_parser.parse_ticks.return_value = pd.DataFrame() # No positions

        kills = extractor.extract_kills()

        assert len(kills) == 1
        assert kills[0].attacker_position is None

    def test_correlate_flash_blinds(self, mock_parser):
        """Test flash correlation with blind events."""
        extractor = EventExtractor(mock_parser)

        # Mock flash detonate
        flash_tick = 500
        thrower_id = '76561198000000001'
        flashes_df = pd.DataFrame([{
            'tick': flash_tick,
            'user_steamid': thrower_id
        }])

        # Mock player blinds
        # 1. Enemy blinded
        # 2. Teammate blinded
        # 3. Self blinded
        blinds_df = pd.DataFrame([
            {
                'tick': flash_tick + 2,
                'user_steamid': 'enemy',
                'user_team_num': 2,
                'attacker_team_num': 3, # Different team
                'blind_duration': 3.0
            },
            {
                'tick': flash_tick + 3,
                'user_steamid': 'teammate',
                'user_team_num': 3,
                'attacker_team_num': 3, # Same team
                'blind_duration': 2.0
            },
            {
                'tick': flash_tick + 4,
                'user_steamid': thrower_id, # Self
                'user_team_num': 3,
                'attacker_team_num': 3,
                'blind_duration': 5.0
            }
        ])

        def parse_event_side_effect(event_name):
            if event_name == "flashbang_detonate":
                return flashes_df
            if event_name == "player_blind":
                return blinds_df
            return pd.DataFrame()

        mock_parser.parse_event.side_effect = parse_event_side_effect

        flashes = extractor.extract_flashes()

        assert len(flashes) == 1
        flash = flashes[0]

        assert flash.enemies_blinded == 1
        assert flash.teammates_blinded == 1
        assert flash.self_flash is True

        # Avg duration: (3.0 + 2.0 + 5.0) / 3 = 3.33
        assert flash.avg_blind_duration == pytest.approx(3.33, 0.01)

    def test_extract_smokes(self, mock_parser):
        """Test smoke extraction."""
        extractor = EventExtractor(mock_parser)

        tick = 1000
        smokes_df = pd.DataFrame([{
            'tick': tick,
            'user_steamid': '1'
        }])

        mock_parser.parse_event.return_value = smokes_df

        smokes = extractor.extract_smokes()

        assert len(smokes) == 1
        smoke = smokes[0]
        assert smoke.start_tick == tick
        # End tick should be start + 18*64
        assert smoke.end_tick == tick + 18 * 64

if __name__ == '__main__':
    pytest.main([__file__, '-v'])

# SPDX-FileCopyrightText: 2026 Pl4yer-ONE <mahadevan.rajeev27@gmail.com>
# SPDX-License-Identifier: LicenseRef-Sacrilege-EULA

"""Unit tests for Intelligence Modules."""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import (
    DemoData, DemoHeader, RoundData, PlayerInfo, KillEvent,
    FlashEvent, SmokeEvent, Team, Vector3, EventType
)
from src.intelligence.crosshair_discipline import CrosshairDisciplineModule
from src.intelligence.utility_intelligence import UtilityIntelligenceModule
from src.intelligence.trade_discipline import TradeDisciplineModule
from src.intelligence.peek_iq import PeekIQModule

@pytest.fixture
def mock_demo_data():
    """Create a mock DemoData object."""
    header = DemoHeader(
        map_name="de_dust2",
        tick_rate=64.0,
        duration_ticks=10000,
        duration_seconds=156.25
    )

    player_id = "76561198000000001"
    teammate_id = "76561198000000002"
    enemy_id = "76561198000000003"

    players = {
        player_id: PlayerInfo(steam_id=player_id, name="TestPlayer", team=Team.CT),
        teammate_id: PlayerInfo(steam_id=teammate_id, name="Teammate", team=Team.CT),
        enemy_id: PlayerInfo(steam_id=enemy_id, name="Enemy", team=Team.T),
    }

    # Round 1
    round1 = RoundData(round_number=1, start_tick=100, end_tick=1000)

    # Events
    # Kill 1: Headshot (Good aim)
    k1 = KillEvent(
        tick=500,
        event_type=EventType.KILL,
        attacker_id=player_id,
        victim_id=enemy_id,
        headshot=True,
        weapon="ak47",
        attacker_position=Vector3(0,0,0),
        victim_position=Vector3(100,0,0)
    )
    round1.kills.append(k1)

    # Kill 2: Body shot (Flick?)
    k2 = KillEvent(
        tick=600,
        event_type=EventType.KILL,
        attacker_id=player_id,
        victim_id=enemy_id,
        headshot=False,
        weapon="ak47",
        attacker_position=Vector3(0,0,0),
        victim_position=Vector3(50,50,0)
    )
    round1.kills.append(k2)

    # Kill 3: Teammate dies to enemy (Trade opportunity)
    k3 = KillEvent(
        tick=700,
        event_type=EventType.KILL,
        attacker_id=enemy_id,
        victim_id=teammate_id,
        headshot=False,
        weapon="glock",
        attacker_position=Vector3(200,200,0),
        victim_position=Vector3(250,250,0)
    )
    round1.kills.append(k3)

    # Kill 4: Player trades enemy (Successful trade)
    k4 = KillEvent(
        tick=750, # 50 ticks later < 1.5s (96 ticks)
        event_type=EventType.KILL,
        attacker_id=player_id,
        victim_id=enemy_id,
        headshot=True,
        weapon="m4a1",
        attacker_position=Vector3(300,250,0),
        victim_position=Vector3(200,200,0)
    )
    round1.kills.append(k4)

    # Flash: Effective
    f1 = FlashEvent(
        tick=400,
        event_type=EventType.FLASH,
        thrower_id=player_id,
        enemies_blinded=2,
        teammates_blinded=0,
        avg_blind_duration=3.0, # Full blind
        self_flash=False
    )
    round1.events.append(f1)

    # Flash: Bad (Self flash)
    f2 = FlashEvent(
        tick=450,
        event_type=EventType.FLASH,
        thrower_id=player_id,
        enemies_blinded=0,
        teammates_blinded=0,
        self_flash=True,
        avg_blind_duration=2.0
    )
    round1.events.append(f2)

    return DemoData(
        header=header,
        players=players,
        rounds=[round1],
        events=[] # Global events if any
    )

class TestCrosshairDiscipline:
    """Test CrosshairDisciplineModule."""

    def test_analyze(self, mock_demo_data):
        module = CrosshairDisciplineModule()
        player_id = "76561198000000001"

        result = module.analyze(mock_demo_data, player_id)

        assert result.module_name == "crosshair_discipline"
        assert result.score.overall_score > 0

        # Check components (kills 1, 2, 4 are by player)
        components = result.score.components
        assert components["total_kills"] == 3
        # HS: k1 (True), k2 (False), k4 (True) -> 2/3
        assert components["head_level_pct"] == pytest.approx(66.6, 0.1)

class TestUtilityIntelligence:
    """Test UtilityIntelligenceModule."""

    def test_analyze(self, mock_demo_data):
        module = UtilityIntelligenceModule()
        player_id = "76561198000000001"

        result = module.analyze(mock_demo_data, player_id)

        assert result.module_name == "utility_intelligence"

        # Check components
        components = result.score.components
        assert components["total_flashes"] == 2
        assert components["effective_flashes"] == 1
        assert components["self_flashes"] == 1

class TestTradeDiscipline:
    """Test TradeDisciplineModule."""

    def test_analyze(self, mock_demo_data):
        module = TradeDisciplineModule()
        player_id = "76561198000000001"

        result = module.analyze(mock_demo_data, player_id)

        assert result.module_name == "trade_discipline"

        # In mock data, teammate died (k3) and player traded (k4) quickly
        # This should count as a perfect trade
        components = result.score.components
        assert components["perfect"] == 1
        assert components["missed"] == 0
        assert components["late"] == 0
        assert result.score.overall_score == 100.0

class TestPeekIQ:
    """Test PeekIQModule."""

    def test_analyze(self, mock_demo_data):
        module = PeekIQModule()
        player_id = "76561198000000001"

        result = module.analyze(mock_demo_data, player_id)

        assert result.module_name == "peek_iq"
        assert result.score.overall_score > 0

        # Kills by player: k1 (HS), k2 (Body), k4 (HS)
        # These are offensive peeks resulting in kills

        # k1: HS -> pre_aim 0.8. Total > 1.2 -> FORCED or higher
        # k2: Body -> pre_aim 0.5. Total < 1.2 maybe?

        analyses = result.raw_data["analyses"]
        assert len(analyses) == 3 # 3 kills by player

        # Check that we have analyses
        assert all(a.resulted_in_kill for a in analyses)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])

# SPDX-FileCopyrightText: 2026 Pl4yer-ONE <mahadevan.rajeev27@gmail.com>
# SPDX-License-Identifier: LicenseRef-Sacrilege-EULA

"""Extended rigorous unit tests for DeathAnalyzer."""

import pytest
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.intelligence.death_analyzer import (
    DeathAnalyzer,
    DeathAnalysis,
    MistakeType,
    PlayerStats,
)

class TestDeathAnalyzerExtended:
    """Rigorous tests for DeathAnalyzer internal logic."""

    @pytest.fixture
    def analyzer(self):
        return DeathAnalyzer()

    def test_count_enemy_angles_collinear(self, analyzer):
        """Test enemy angle counting with collinear enemies."""
        victim_pos = (0, 0)
        # Enemies in a line relative to victim: (100, 0) and (200, 0) - same angle (0 rad)
        enemies = [
            {'x': 100, 'y': 0, 'alive': True},
            {'x': 200, 'y': 0, 'alive': True}
        ]

        # Should be 1 angle because they are in the same sector
        angles = analyzer._count_enemy_angles(victim_pos, enemies)
        assert angles == 1

    def test_count_enemy_angles_orthogonal(self, analyzer):
        """Test enemy angle counting with orthogonal enemies."""
        victim_pos = (0, 0)
        # Enemies at 0 and 90 degrees
        enemies = [
            {'x': 100, 'y': 0, 'alive': True},
            {'x': 0, 'y': 100, 'alive': True}
        ]

        # Should be 2 angles (different sectors)
        angles = analyzer._count_enemy_angles(victim_pos, enemies)
        assert angles == 2

    def test_count_enemy_angles_surrounded(self, analyzer):
        """Test enemy angle counting when surrounded."""
        victim_pos = (0, 0)
        # Enemies at 0, 90, 180, 270 degrees
        enemies = [
            {'x': 100, 'y': 0, 'alive': True},
            {'x': 0, 'y': 100, 'alive': True},
            {'x': -100, 'y': 0, 'alive': True},
            {'x': 0, 'y': -100, 'alive': True},
        ]

        angles = analyzer._count_enemy_angles(victim_pos, enemies)
        assert angles == 4

    def test_was_victim_flashed_boundary(self, analyzer):
        """Test flash detection boundaries."""
        # FLASH_EFFECT_TICKS = 96
        # Distance < 800

        victim_pos = (0, 0)
        tick = 1000

        # Case 1: Within time and distance
        flashes = [{'x': 100, 'y': 0, 'start': 950}] # 1000 is within 950 + 96
        assert analyzer._was_victim_flashed(victim_pos, flashes, tick) is True

        # Case 2: Too far distance
        flashes = [{'x': 801, 'y': 0, 'start': 950}]
        assert analyzer._was_victim_flashed(victim_pos, flashes, tick) is False

        # Case 3: Too late (expired)
        flashes = [{'x': 100, 'y': 0, 'start': 900}] # 900 + 96 = 996 < 1000
        assert analyzer._was_victim_flashed(victim_pos, flashes, tick) is False

        # Case 4: Too early (hasn't popped yet?) - assuming 'start' is pop tick
        flashes = [{'x': 100, 'y': 0, 'start': 1001}]
        assert analyzer._was_victim_flashed(victim_pos, flashes, tick) is False

    def test_in_molotov_boundary(self, analyzer):
        """Test molotov detection boundaries."""
        # Radius < 180

        victim_pos = (0, 0)
        tick = 1000

        # Case 1: Inside
        mollies = [{'x': 0, 'y': 0, 'start': 900, 'end': 1100}]
        assert analyzer._in_molotov(victim_pos, mollies, tick) is True

        # Case 2: Edge distance (exact boundary check)
        # Using 179 to be safe inside
        mollies = [{'x': 179, 'y': 0, 'start': 900, 'end': 1100}]
        assert analyzer._in_molotov(victim_pos, mollies, tick) is True

        # Using 181 to be safe outside
        mollies = [{'x': 181, 'y': 0, 'start': 900, 'end': 1100}]
        assert analyzer._in_molotov(victim_pos, mollies, tick) is False

        # Case 3: Before start
        mollies = [{'x': 0, 'y': 0, 'start': 1001, 'end': 1100}]
        assert analyzer._in_molotov(victim_pos, mollies, tick) is False

        # Case 4: After end
        mollies = [{'x': 0, 'y': 0, 'start': 800, 'end': 999}]
        assert analyzer._in_molotov(victim_pos, mollies, tick) is False

    def test_blame_score_combinations(self):
        """Test blame score calculation with various modifiers."""

        # Helper to make analysis object
        def make_analysis(severity, distance=500, enemies=1, traded=False, flashed=False):
            return DeathAnalysis(
                victim_name="Test", victim_team="CT", attacker_name="T",
                tick=1000, round_num=1, position=(0,0),
                mistakes=[], reasons=[],
                severity=severity,
                was_tradeable=True, was_traded=traded,
                teammate_distance=distance,
                was_flashed=flashed,
                in_utility=False,
                enemy_count=enemies,
                teammate_count=1
            )

        # Base severity 5 -> 100
        a = make_analysis(severity=5)
        assert a.blame_score() == 100

        # Severity 5 + Isolated (>1000 dist) -> 100 + 10 -> capped at 100
        a = make_analysis(severity=5, distance=1500)
        assert a.blame_score() == 100

        # Severity 4 -> 80 + Isolated -> 90
        a = make_analysis(severity=4, distance=1500)
        assert a.blame_score() == 90

        # Severity 5 + Many enemies (>=3) -> 100 - 10 = 90
        a = make_analysis(severity=5, enemies=3)
        assert a.blame_score() == 90

        # Severity 5 + Traded -> 100 - 15 = 85
        a = make_analysis(severity=5, traded=True)
        assert a.blame_score() == 85

        # Severity 5 + Flashed -> 100 - 5 = 95
        a = make_analysis(severity=5, flashed=True)
        assert a.blame_score() == 95

        # All modifiers: Severity 5, Isolated(+10), Many Enemies(-10), Traded(-15), Flashed(-5)
        # 100 + 10 - 10 - 15 - 5 = 80
        a = make_analysis(severity=5, distance=1500, enemies=3, traded=True, flashed=True)
        assert a.blame_score() == 80

        # Minimum clamp check
        # Severity 1 -> 20. Traded(-15), Flashed(-5), Many enemies(-10) -> 20 - 15 - 5 - 10 = -10 -> 0
        a = make_analysis(severity=1, enemies=3, traded=True, flashed=True)
        assert a.blame_score() == 0

    def test_nearest_teammate_distance_empty(self, analyzer):
        """Test distance when no teammates are alive."""
        dist = analyzer._nearest_teammate_distance((0,0), [])
        assert dist == 9999

    def test_check_if_traded_window(self, analyzer):
        """Test trade window boundaries."""
        # TRADE_WINDOW_TICKS = 192
        victim_death_tick = 1000
        attacker = "BadGuy"

        # Case 1: Traded immediately
        recent_kills = [{'victim': attacker, 'tick': 1001}]
        assert analyzer._check_if_traded(attacker, recent_kills, victim_death_tick) is True

        # Case 2: Traded at limit
        recent_kills = [{'victim': attacker, 'tick': 1000 + 192}]
        assert analyzer._check_if_traded(attacker, recent_kills, victim_death_tick) is True

        # Case 3: Traded too late
        recent_kills = [{'victim': attacker, 'tick': 1000 + 193}]
        assert analyzer._check_if_traded(attacker, recent_kills, victim_death_tick) is False

        # Case 4: Kill happened before victim death (not a trade)
        recent_kills = [{'victim': attacker, 'tick': 1000}] # exact same tick? usually trade is subsequent
        # The code checks tick < k_tick. So 1000 < 1000 is False.
        assert analyzer._check_if_traded(attacker, recent_kills, victim_death_tick) is False

    def test_full_analysis_logic_isolated(self, analyzer):
        """Test that ISOLATED logic triggers correctly."""
        # ISOLATED_DISTANCE = 900

        kill = {'victim': 'V', 'victim_team': 'CT', 'attacker': 'A'}
        players = [
            {'name': 'V', 'team': 'CT', 'x': 0, 'y': 0, 'alive': False},
            {'name': 'T1', 'team': 'CT', 'x': 1000, 'y': 0, 'alive': True}, # > 900 away
            {'name': 'A', 'team': 'T', 'x': 100, 'y': 0, 'alive': True}
        ]

        analysis = analyzer.analyze_death(
            kill, players, [], [], [], [], 1000, 1
        )

        assert MistakeType.ISOLATED in analysis.mistakes
        assert analysis.severity == 5

    def test_full_analysis_crossfire(self, analyzer):
        """Test that CROSSFIRE logic triggers correctly."""
        kill = {'victim': 'V', 'victim_team': 'CT', 'attacker': 'A'}
        players = [
            {'name': 'V', 'team': 'CT', 'x': 0, 'y': 0, 'alive': False},
            {'name': 'A', 'team': 'T', 'x': 100, 'y': 0, 'alive': True}, # 0 deg
            {'name': 'E2', 'team': 'T', 'x': 0, 'y': 100, 'alive': True}  # 90 deg
        ]

        analysis = analyzer.analyze_death(
            kill, players, [], [], [], [], 1000, 1
        )

        assert MistakeType.CROSSFIRE in analysis.mistakes

    def test_full_analysis_outnumbered(self, analyzer):
        """Test OUTNUMBERED logic."""
        # OUTNUMBERED if enemy_count > teammate_count + 2

        kill = {'victim': 'V', 'victim_team': 'CT', 'attacker': 'A'}
        players = [
            {'name': 'V', 'team': 'CT', 'x': 0, 'y': 0, 'alive': False},
            # 0 Teammates alive
            # 3 Enemies alive (+1 attacker = 4 enemies total)
            {'name': 'A', 'team': 'T', 'x': 100, 'y': 0, 'alive': True},
            {'name': 'E2', 'team': 'T', 'x': 100, 'y': 10, 'alive': True},
            {'name': 'E3', 'team': 'T', 'x': 100, 'y': 20, 'alive': True},
            {'name': 'E4', 'team': 'T', 'x': 100, 'y': 30, 'alive': True},
        ]

        # enemy_count = 4. teammate_count = 0.
        # 4 > 0 + 2 -> True.
        # Since teammate_count == 0, it should be CLUTCH_ATTEMPT, not OUTNUMBERED

        analysis = analyzer.analyze_death(
            kill, players, [], [], [], [], 1000, 1
        )

        assert MistakeType.CLUTCH_ATTEMPT in analysis.mistakes
        assert MistakeType.OUTNUMBERED not in analysis.mistakes

        # Now add a teammate so it's not a clutch
        players.append({'name': 'T1', 'team': 'CT', 'x': 0, 'y': 10, 'alive': True})
        # enemy_count = 4. teammate_count = 1.
        # 4 > 1 + 2 (3) -> True.

        analysis = analyzer.analyze_death(
            kill, players, [], [], [], [], 1000, 1
        )

        assert MistakeType.OUTNUMBERED in analysis.mistakes

if __name__ == '__main__':
    pytest.main([__file__, '-v'])

# SPDX-FileCopyrightText: 2026 Pl4yer-ONE <mahadevan.rajeev27@gmail.com>
# SPDX-License-Identifier: LicenseRef-Sacrilege-EULA

"""Integration tests for demo parsing and analysis pipeline."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDemoParser:
    """Test demo parsing with demoparser2."""
    
    @pytest.fixture
    def demo_path(self):
        """Get path to test demo."""
        return Path("demo files/gamerlegion-vs-venom-m2-dust2.dem")
    
    def test_demo_exists(self, demo_path):
        """Demo file should exist."""
        assert demo_path.exists(), f"Demo not found: {demo_path}"
    
    def test_parse_header(self, demo_path):
        """Should parse demo header."""
        from demoparser2 import DemoParser
        parser = DemoParser(str(demo_path))
        header = parser.parse_header()
        
        assert 'map_name' in header
        assert header['map_name'] == 'de_dust2'
    
    def test_parse_kills(self, demo_path):
        """Should parse kill events."""
        from demoparser2 import DemoParser
        parser = DemoParser(str(demo_path))
        kills = parser.parse_event("player_death")
        
        assert len(kills) > 0
        assert 'attacker_name' in kills.columns
        assert 'user_name' in kills.columns
    
    def test_parse_positions(self, demo_path):
        """Should parse player positions."""
        from demoparser2 import DemoParser
        parser = DemoParser(str(demo_path))
        ticks = parser.parse_ticks(["X", "Y", "Z", "team_num"])
        
        assert len(ticks) > 0
        assert 'X' in ticks.columns
        assert 'Y' in ticks.columns


class TestAnalysisPipeline:
    """Test full analysis pipeline."""
    
    @pytest.fixture
    def demo_path(self):
        return Path("demo files/gamerlegion-vs-venom-m2-dust2.dem")
    
    def test_full_pipeline(self, demo_path):
        """Run full analysis pipeline."""
        from demoparser2 import DemoParser
        from src.intelligence.death_analyzer import DeathAnalyzer
        
        # Parse
        parser = DemoParser(str(demo_path))
        kills = parser.parse_event("player_death", other=["total_rounds_played"])
        ticks = parser.parse_ticks(["X", "Y", "team_num", "is_alive"])
        
        # Analyze
        analyzer = DeathAnalyzer()
        
        deaths_analyzed = 0
        for _, kill in kills.head(10).iterrows():
            tick = int(kill.get('tick', 0))
            tick_data = ticks[ticks['tick'] == tick]
            
            players = []
            for _, p in tick_data.iterrows():
                team_num = p.get('team_num', 0)
                players.append({
                    'name': p.get('name', ''),
                    'team': 'CT' if team_num == 3 else 'T',
                    'x': float(p.get('X', 0)),
                    'y': float(p.get('Y', 0)),
                    'health': 0,
                    'alive': False,
                })
            
            kill_data = {
                'attacker': kill.get('attacker_name', ''),
                'attacker_team': 'T',
                'victim': kill.get('user_name', ''),
                'victim_team': 'CT',
                'victim_id': str(kill.get('user_steamid', '')),
                'weapon': kill.get('weapon', ''),
                'hs': bool(kill.get('headshot', False)),
            }
            
            analysis = analyzer.analyze_death(kill_data, players, [], [], [], [], tick, 1)
            deaths_analyzed += 1
            
            assert analysis.victim_name == kill_data['victim']
            assert len(analysis.mistakes) > 0
        
        assert deaths_analyzed == 10
    
    def test_rankings_generated(self, demo_path):
        """Rankings should be generated after analysis."""
        from demoparser2 import DemoParser
        from src.intelligence.death_analyzer import DeathAnalyzer
        
        parser = DemoParser(str(demo_path))
        kills = parser.parse_event("player_death")
        
        analyzer = DeathAnalyzer()
        
        # Add some kills
        for _, kill in kills.head(5).iterrows():
            attacker = kill.get('attacker_name', 'Unknown')
            analyzer.update_kill(attacker, 'T')
        
        rankings = analyzer.get_rankings()
        assert len(rankings) > 0
        assert all(hasattr(r, 'rank_grade') for r in rankings)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

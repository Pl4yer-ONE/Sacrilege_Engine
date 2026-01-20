# SPDX-FileCopyrightText: 2026 Pl4yer-ONE <mahadevan.rajeev27@gmail.com>
# SPDX-License-Identifier: LicenseRef-Sacrilege-EULA
#
# Sacrilege Engine - CS2 Demo Intelligence System
# https://github.com/Pl4yer-ONE/Sacrilege_Engine

"""
SACRILEGE RADAR - Ultimate CS2 Demo Replay Viewer
Professional visualization with full statistics and animations
"""

import pygame
import sys
import math
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Team, Vector3


@dataclass
class MapConfig:
    name: str
    display_name: str
    pos_x: float
    pos_y: float
    scale: float
    
    def world_to_radar(self, wx: float, wy: float, size: int) -> tuple:
        px = (wx - self.pos_x) / self.scale
        py = (self.pos_y - wy) / self.scale
        return int(max(0, min(size - 1, px))), int(max(0, min(size - 1, py)))


MAP_CONFIGS = {
    'de_mirage': MapConfig('de_mirage', 'MIRAGE', -3230, 1713, 5.0),
    'de_dust2': MapConfig('de_dust2', 'DUST II', -2476, 3239, 4.4),
    'de_inferno': MapConfig('de_inferno', 'INFERNO', -2087, 3870, 4.9),
    'de_ancient': MapConfig('de_ancient', 'ANCIENT', -2953, 2164, 5.0),
    'de_nuke': MapConfig('de_nuke', 'NUKE', -3453, 2887, 7.0),
    'de_overpass': MapConfig('de_overpass', 'OVERPASS', -4831, 1781, 5.2),
    'de_anubis': MapConfig('de_anubis', 'ANUBIS', -2796, 3328, 5.22),
    'de_vertigo': MapConfig('de_vertigo', 'VERTIGO', -3168, 1762, 4.0),
}


class Theme:
    """Professional color scheme."""
    BG = (8, 10, 14)
    PANEL = (14, 18, 24)
    CARD = (20, 26, 34)
    CARD_HOVER = (28, 36, 48)
    BORDER = (35, 45, 60)
    
    CT = (75, 150, 255)
    CT_LIGHT = (120, 180, 255)
    CT_DARK = (40, 90, 160)
    T = (255, 180, 50)
    T_LIGHT = (255, 210, 100)
    T_DARK = (170, 120, 35)
    
    ACCENT = (0, 200, 255)
    ACCENT2 = (200, 100, 255)
    SUCCESS = (60, 210, 110)
    WARNING = (255, 170, 50)
    DANGER = (235, 60, 60)
    
    WHITE = (240, 245, 255)
    GRAY = (110, 125, 145)
    MUTED = (60, 70, 85)
    
    SMOKE = (170, 180, 195)
    FIRE = (255, 95, 35)
    FLASH = (255, 255, 170)
    HE = (255, 85, 85)
    BOMB_GLOW = (255, 50, 50)


class RadarReplayer:
    """Ultimate CS2 radar replay viewer."""
    
    def __init__(self, width: int = 1500, height: int = 920):
        pygame.init()
        pygame.font.init()
        
        self.width = width
        self.height = height
        self.radar_size = 640
        
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("SACRILEGE RADAR - CS2 Demo Viewer")
        
        self.clock = pygame.time.Clock()
        self.frame = 0
        self.fps = 0
        self.fps_timer = 0
        
        # Fonts with fallbacks - LARGER SIZES
        try:
            self.font_xl = pygame.font.SysFont('SF Pro Display', 36, bold=True)
            self.font_lg = pygame.font.SysFont('SF Pro Display', 22, bold=True)
            self.font_md = pygame.font.SysFont('SF Pro Text', 16)
            self.font_sm = pygame.font.SysFont('SF Pro Text', 14)
            self.font_xs = pygame.font.SysFont('SF Pro Text', 11)
        except Exception:
            self.font_xl = pygame.font.SysFont('Arial', 36, bold=True)
            self.font_lg = pygame.font.SysFont('Arial', 22, bold=True)
            self.font_md = pygame.font.SysFont('Arial', 16)
            self.font_sm = pygame.font.SysFont('Arial', 14)
            self.font_xs = pygame.font.SysFont('Arial', 11)
        
        # State
        self.demo_data = None
        self.map_config = None
        self.map_image = None
        self.map_scaled = None
        
        self.is_playing = False
        self.speed = 1.0
        
        # Data
        self.tick_df: Optional[pd.DataFrame] = None
        self.all_ticks: List[int] = []
        self.tick_idx = 0
        
        self.players: Dict[str, dict] = {}
        self.rounds: List[tuple] = []
        self.kills_by_tick: Dict[int, list] = {}
        self.current_round = 1
        
        # Utility
        self.smokes = []
        self.mollies = []
        self.flashes = []
        self.he_nades = []
        
        # Stats
        self.round_kills = {'CT': 0, 'T': 0}
        self.total_kills = {'CT': 0, 'T': 0}
        self.recent_kills = []
        
        # Animations
        self.kill_animations = []  # [(x, y, start_tick, team)]
        self.damage_indicators = []
        
        # Bomb state
        self.bomb_planted = False
        self.bomb_position = None
        self.bomb_plant_tick = 0
        
        # Death Analyzer
        self.death_analyzer = None
        self.death_popups = []  # [(analysis, show_until_tick)]
        self.analyzed_kills = set()  # Track which kills we've analyzed
        self.show_round_summary = False
        self.round_summary_tick = 0
        
    def load_demo(self, demo_path: Path) -> bool:
        from demoparser2 import DemoParser as DP2
        from src.parser.demo_parser import DemoParser
        
        print(f"Loading: {demo_path.name}")
        
        try:
            parser = DemoParser()
            result = parser.parse(demo_path)
            if not result.success:
                print(f"Parse error: {result.error}")
                return False
            
            self.demo_data = result.data
            map_name = self.demo_data.header.map_name
            self.map_config = MAP_CONFIGS.get(map_name, MAP_CONFIGS['de_mirage'])
            
            self._load_map(map_name)
            
            # Players
            for pid, p in self.demo_data.players.items():
                self.players[pid] = {'name': p.name, 'team': p.team.name, 'kills': 0, 'deaths': 0}
            
            # Rounds and kills
            for rd in self.demo_data.rounds:
                self.rounds.append((rd.start_tick, rd.end_tick, rd.round_number))
                for k in rd.kills:
                    if k.tick not in self.kills_by_tick:
                        self.kills_by_tick[k.tick] = []
                    
                    # Track player stats
                    if k.attacker_id in self.players:
                        self.players[k.attacker_id]['kills'] += 1
                    if k.victim_id in self.players:
                        self.players[k.victim_id]['deaths'] += 1
                    
                    self.kills_by_tick[k.tick].append({
                        'attacker': self.players.get(k.attacker_id, {}).get('name', '?'),
                        'victim': self.players.get(k.victim_id, {}).get('name', '?'),
                        'attacker_team': self.players.get(k.attacker_id, {}).get('team', 'CT'),
                        'weapon': k.weapon,
                        'hs': k.headshot,
                        'tick': k.tick,
                        'attacker_pos': k.attacker_position,
                        'victim_pos': k.victim_position,
                    })
            
            # Tick data
            print("Extracting positions...")
            dp2 = DP2(str(demo_path))
            data = dp2.parse_ticks([
                "X", "Y", "Z", "yaw", "health", "is_alive", 
                "armor_value", "has_defuser", "has_bomb", 
                "current_equip_value", "active_weapon_name"
            ])
            
            if isinstance(data, pd.DataFrame):
                ticks = sorted(data['tick'].unique())
                sampled = ticks[::4]
                self.tick_df = data[data['tick'].isin(sampled)]
                self.all_ticks = sorted(self.tick_df['tick'].unique())
            
            # Utility
            print("Extracting utility...")
            self._extract_utility(dp2)
            
            # Bomb events
            self._extract_bomb_events(dp2)
            
            # Initialize Death Analyzer
            from src.intelligence.death_analyzer import DeathAnalyzer
            self.death_analyzer = DeathAnalyzer()
            print("✓ Death analyzer initialized")
            
            print(f"✓ Loaded: {len(self.all_ticks)} ticks, {len(self.rounds)} rounds")
            print(f"✓ Utility: {len(self.smokes)} smokes, {len(self.mollies)} fires, {len(self.flashes)} flashes, {len(self.he_nades)} HEs")
            return True
            
        except Exception as e:
            print(f"Load error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_map(self, name):
        path = Path(__file__).parent / 'maps' / f"{name}.png"
        if path.exists():
            try:
                self.map_image = pygame.image.load(str(path))
                self.map_scaled = pygame.transform.smoothscale(self.map_image, (self.radar_size, self.radar_size))
                print(f"✓ Map loaded: {name}")
            except Exception as e:
                print(f"Map load failed: {e}")
    
    def _extract_utility(self, dp2):
        try:
            for _, r in dp2.parse_event("smokegrenade_detonate").iterrows():
                self.smokes.append({'x': r['x'], 'y': r['y'], 'start': r['tick'], 'end': r['tick'] + 1152})
        except: pass
        try:
            for _, r in dp2.parse_event("inferno_startburn").iterrows():
                self.mollies.append({'x': r['x'], 'y': r['y'], 'start': r['tick'], 'end': r['tick'] + 448})
        except: pass
        try:
            for _, r in dp2.parse_event("flashbang_detonate").iterrows():
                self.flashes.append({'x': r['x'], 'y': r['y'], 'start': r['tick'], 'end': r['tick'] + 40})
        except: pass
        try:
            for _, r in dp2.parse_event("hegrenade_detonate").iterrows():
                self.he_nades.append({'x': r['x'], 'y': r['y'], 'start': r['tick'], 'end': r['tick'] + 30})
        except: pass
    
    def _extract_bomb_events(self, dp2):
        try:
            plants = dp2.parse_event("bomb_planted")
            if isinstance(plants, pd.DataFrame) and len(plants) > 0:
                pass  # Would track bomb plants here
        except: pass
    
    def run(self):
        running = True
        last_tick_time = pygame.time.get_ticks()
        
        while running:
            self.frame += 1
            
            # FPS calculation
            now = pygame.time.get_ticks()
            if now - self.fps_timer > 1000:
                self.fps = self.clock.get_fps()
                self.fps_timer = now
            
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == pygame.KEYDOWN:
                    self._handle_key(e)
                elif e.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_click(e)
                elif e.type == pygame.VIDEORESIZE:
                    self.width, self.height = e.w, e.h
                    self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
            
            # Playback
            if self.is_playing and self.all_ticks:
                if now - last_tick_time > 25 / self.speed:
                    self.tick_idx = min(self.tick_idx + 1, len(self.all_ticks) - 1)
                    last_tick_time = now
                    self._update()
            
            self._render()
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
    
    def _handle_key(self, e):
        if e.key == pygame.K_SPACE:
            self.is_playing = not self.is_playing
        elif e.key == pygame.K_LEFT:
            self.tick_idx = max(0, self.tick_idx - 60)
            self._update()
        elif e.key == pygame.K_RIGHT:
            self.tick_idx = min(len(self.all_ticks) - 1, self.tick_idx + 60)
            self._update()
        elif e.key == pygame.K_UP:
            self.speed = min(8.0, self.speed * 2)
        elif e.key == pygame.K_DOWN:
            self.speed = max(0.25, self.speed / 2)
        elif e.key == pygame.K_r:
            self._next_round()
        elif e.key == pygame.K_e:
            self._prev_round()
        elif e.key == pygame.K_HOME:
            self.tick_idx = 0
            self._update()
        elif e.key == pygame.K_END:
            self.tick_idx = len(self.all_ticks) - 1
            self._update()
        elif e.key == pygame.K_F12:
            self._take_screenshot()
        elif e.key == pygame.K_h:
            self.show_help = not getattr(self, 'show_help', False)
        elif e.key == pygame.K_f:
            pygame.display.toggle_fullscreen()
    
    def _take_screenshot(self):
        """Save screenshot to Downloads folder."""
        from datetime import datetime
        downloads = Path.home() / "Downloads"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = downloads / f"sacrilege_screenshot_{timestamp}.png"
        pygame.image.save(self.screen, str(filename))
        print(f"✓ Screenshot saved: {filename}")
    
    def _next_round(self):
        if not self.all_ticks: return
        t = self.all_ticks[self.tick_idx]
        for s, e, n in self.rounds:
            if s > t:
                for i, tick in enumerate(self.all_ticks):
                    if tick >= s:
                        self.tick_idx = i
                        self._update()
                        return
    
    def _prev_round(self):
        if not self.all_ticks: return
        t = self.all_ticks[self.tick_idx]
        for s, e, n in reversed(self.rounds):
            if e < t:
                for i, tick in enumerate(self.all_ticks):
                    if tick >= s:
                        self.tick_idx = i
                        self._update()
                        return
    
    def _handle_click(self, e):
        x, y = e.pos
        # Timeline click
        ty = self.height - 42
        tx, tw = 380, self.width - 420
        if ty - 10 <= y <= ty + 30 and tx <= x <= tx + tw and self.all_ticks:
            self.tick_idx = int((x - tx) / tw * (len(self.all_ticks) - 1))
            self._update()
    
    def _update(self):
        if not self.all_ticks: return
        tick = self.all_ticks[self.tick_idx]
        
        # Current round
        prev_round = self.current_round
        for s, e, n in self.rounds:
            if s <= tick <= e:
                self.current_round = n
                break
        
        # Reset on round change
        if self.current_round != prev_round:
            self.round_kills = {'CT': 0, 'T': 0}
            self.recent_kills.clear()
            self.kill_animations.clear()
            self.analyzed_kills.clear()  # Reset for new round
            if self.death_analyzer:
                self.death_analyzer.reset_round()
        
        # Kill feed and death analysis
        round_start = next((s for s, e, n in self.rounds if n == self.current_round), 0)
        
        # Process kills in this round
        for kt, kills in self.kills_by_tick.items():
            if round_start <= kt <= tick:
                for k in kills:
                    kill_id = f"{kt}_{k['victim']}"
                    
                    # Only process each kill once
                    if kill_id not in self.analyzed_kills:
                        self.analyzed_kills.add(kill_id)
                        
                        # Add to recent kills for display
                        self.recent_kills.append(k)
                        
                        # Count round kills
                        team = k['attacker_team']
                        self.round_kills[team] = self.round_kills.get(team, 0) + 1
                        
                        # Add kill animation
                        if k.get('victim_pos'):
                            self.kill_animations.append({
                                'x': k['victim_pos'].x,
                                'y': k['victim_pos'].y,
                                'tick': kt,
                                'hs': k['hs'],
                            })
                        
                        # DEATH ANALYSIS
                        if self.death_analyzer:
                            # Track kill for rankings
                            self.death_analyzer.update_kill(k['attacker'], k['attacker_team'])
                            
                            # Get players at tick BEFORE death
                            pre_kill_tick = max(0, kt - 8)
                            players = self._get_players_for_analysis(pre_kill_tick, k['victim'])
                            
                            # Find victim's team
                            victim_team = 'T'
                            for p in players:
                                if p['name'] == k['victim']:
                                    victim_team = p['team']
                                    break
                            k['victim_team'] = victim_team
                            k['victim_id'] = ''
                            
                            # Analyze the death
                            analysis = self.death_analyzer.analyze_death(
                                k, players, self.smokes, self.mollies, 
                                self.flashes, self.recent_kills, kt, self.current_round
                            )
                            
                            # Add popup (show for 5 seconds = 320 ticks)
                            self.death_popups.append((analysis, kt + 320))
        
        # Trim old kills from feed
        self.recent_kills = [k for k in self.recent_kills if tick - k['tick'] < 400]
        
        # Clean old animations and popups
        self.kill_animations = [a for a in self.kill_animations if tick - a['tick'] < 64]
        self.death_popups = [(a, t) for a, t in self.death_popups if t > tick]
    
    def _get_players(self, tick):
        if self.tick_df is None: return []
        
        data = self.tick_df[self.tick_df['tick'] == tick]
        players = []
        
        for _, row in data.iterrows():
            sid = str(row.get('steamid', ''))
            if sid not in self.players: continue
            
            info = self.players[sid]
            alive = bool(row.get('is_alive', True))
            hp = int(row.get('health', 0))
            if hp > 0: alive = True
            
            players.append({
                'id': sid,
                'name': info['name'],
                'team': info['team'],
                'kills': info.get('kills', 0),
                'deaths': info.get('deaths', 0),
                'x': float(row.get('X', 0)),
                'y': float(row.get('Y', 0)),
                'yaw': float(row.get('yaw', 0)),
                'hp': hp if alive else 0,
                'armor': int(row.get('armor_value', 0)),
                'alive': alive,
                'bomb': bool(row.get('has_bomb', False)),
                'defuser': bool(row.get('has_defuser', False)),
                'equip': int(row.get('current_equip_value', 0)),
                'weapon': str(row.get('active_weapon_name', ''))[:12],
            })
        
        return players
    
    def _get_players_for_analysis(self, target_tick: int, victim_name: str):
        """Get players at closest available tick for death analysis."""
        if self.tick_df is None:
            return []
        
        # Find nearest tick in our sampled data
        available_ticks = self.tick_df['tick'].unique()
        nearest_tick = min(available_ticks, key=lambda t: abs(t - target_tick))
        
        data = self.tick_df[self.tick_df['tick'] == nearest_tick]
        players = []
        
        for _, row in data.iterrows():
            sid = str(row.get('steamid', ''))
            if sid not in self.players:
                continue
            
            info = self.players[sid]
            hp = int(row.get('health', 0))
            alive = hp > 0 or bool(row.get('is_alive', False))
            
            # The victim was alive before this death
            if info['name'] == victim_name:
                alive = True
                hp = max(hp, 1)
            
            players.append({
                'id': sid,
                'name': info['name'],
                'team': info['team'],
                'x': float(row.get('X', 0)),
                'y': float(row.get('Y', 0)),
                'alive': alive,
                'hp': hp,
            })
        
        return players
    
    def _render(self):
        self.screen.fill(Theme.BG)
        
        if not self.all_ticks:
            self._render_loading()
            return
        
        tick = self.all_ticks[self.tick_idx]
        players = self._get_players(tick)
        
        self._draw_header(tick)
        self._draw_scoreboard(players)
        self._draw_player_list(players)
        self._draw_radar(players, tick)
        self._draw_killfeed()
        self._draw_death_panel()  # NEW: Death analysis panel
        self._draw_round_stats(players)
        self._draw_timeline(tick)
        self._draw_legend()
        self._draw_death_popups(tick)  # NEW: Death popups on radar
    
    def _render_loading(self):
        # Animated loading
        dots = "." * ((self.frame // 20) % 4)
        txt = self.font_xl.render(f"Loading{dots}", True, Theme.ACCENT)
        self.screen.blit(txt, (self.width//2 - txt.get_width()//2, self.height//2))
    
    def _draw_header(self, tick):
        # Header bar
        pygame.draw.rect(self.screen, Theme.PANEL, (0, 0, self.width, 52))
        
        # Animated logo
        pulse = 0.5 + abs(math.sin(self.frame * 0.03)) * 0.5
        r, g, b = Theme.ACCENT
        glow = (r, int(g * pulse + 55), b)
        logo = self.font_xl.render("SACRILEGE", True, glow)
        self.screen.blit(logo, (15, 10))
        
        # Subtitle
        sub = self.font_xs.render("CS2 DEMO VIEWER", True, Theme.GRAY)
        self.screen.blit(sub, (18, 38))
        
        # Accent line with gradient effect
        for i in range(3):
            alpha = 255 - i * 60
            pygame.draw.line(self.screen, (*Theme.ACCENT[:3],), (0, 51 - i), (self.width, 51 - i), 1)
        
        # Playback info
        state = "▶ PLAYING" if self.is_playing else "⏸ PAUSED"
        state_color = Theme.SUCCESS if self.is_playing else Theme.WARNING
        self.screen.blit(self.font_md.render(state, True, state_color), (self.width - 180, 12))
        
        speed_txt = f"{self.speed}x"
        self.screen.blit(self.font_md.render(speed_txt, True, Theme.ACCENT), (self.width - 180, 30))
        
        # FPS
        fps_txt = f"{int(self.fps)} FPS"
        self.screen.blit(self.font_xs.render(fps_txt, True, Theme.MUTED), (self.width - 60, 20))
    
    def _draw_scoreboard(self, players):
        cx = self.width // 2
        sy = 58
        
        ct_alive = sum(1 for p in players if p['team'] == 'CT' and p['alive'])
        t_alive = sum(1 for p in players if p['team'] == 'T' and p['alive'])
        
        # CT box
        pygame.draw.rect(self.screen, Theme.CT_DARK, (cx - 185, sy, 160, 48), border_radius=6)
        pygame.draw.rect(self.screen, Theme.CT, (cx - 185, sy, 4, 48), border_top_left_radius=6, border_bottom_left_radius=6)
        self.screen.blit(self.font_lg.render("CT", True, Theme.CT_LIGHT), (cx - 175, sy + 8))
        
        # CT alive indicator dots
        for i in range(5):
            color = Theme.CT if i < ct_alive else Theme.MUTED
            pygame.draw.circle(self.screen, color, (cx - 170 + i * 18, sy + 38), 5)
        
        # Center - Map and Round
        pygame.draw.rect(self.screen, Theme.CARD, (cx - 55, sy, 110, 48), border_radius=6)
        map_txt = self.map_config.display_name if self.map_config else "UNKNOWN"
        self.screen.blit(self.font_sm.render(map_txt, True, Theme.GRAY), (cx - 30, sy + 6))
        rd = self.font_lg.render(f"R{self.current_round}", True, Theme.WHITE)
        self.screen.blit(rd, (cx - rd.get_width()//2, sy + 24))
        
        # T box
        pygame.draw.rect(self.screen, Theme.T_DARK, (cx + 25, sy, 160, 48), border_radius=6)
        pygame.draw.rect(self.screen, Theme.T, (cx + 181, sy, 4, 48), border_top_right_radius=6, border_bottom_right_radius=6)
        self.screen.blit(self.font_lg.render("T", True, Theme.T_LIGHT), (cx + 155, sy + 8))
        
        # T alive indicator dots
        for i in range(5):
            color = Theme.T if i < t_alive else Theme.MUTED
            pygame.draw.circle(self.screen, color, (cx + 35 + i * 18, sy + 38), 5)
    
    def _draw_player_list(self, players):
        px, py = 12, 115
        pw = 350
        
        # CT Section
        pygame.draw.rect(self.screen, Theme.PANEL, (px, py, pw, 30), border_radius=5)
        pygame.draw.rect(self.screen, Theme.CT, (px, py, 4, 30), border_top_left_radius=5, border_bottom_left_radius=5)
        self.screen.blit(self.font_lg.render("COUNTER-TERRORISTS", True, Theme.CT), (px + 12, py + 6))
        
        cy = py + 34
        for p in sorted(players, key=lambda x: (-x['alive'], -x['hp'], x['name'])):
            if p['team'] == 'CT':
                self._draw_player_card(p, px, cy, pw)
                cy += 54
        
        # T Section
        ty = cy + 12
        pygame.draw.rect(self.screen, Theme.PANEL, (px, ty, pw, 30), border_radius=5)
        pygame.draw.rect(self.screen, Theme.T, (px, ty, 4, 30), border_top_left_radius=5, border_bottom_left_radius=5)
        self.screen.blit(self.font_lg.render("TERRORISTS", True, Theme.T), (px + 12, ty + 6))
        
        ty += 34
        for p in sorted(players, key=lambda x: (-x['alive'], -x['hp'], x['name'])):
            if p['team'] == 'T':
                self._draw_player_card(p, px, ty, pw)
                ty += 54
    
    def _draw_player_card(self, p, x, y, w):
        h = 50
        alive = p['alive']
        
        # Background with hover-like effect for alive
        bg = Theme.CARD if alive else (16, 18, 22)
        pygame.draw.rect(self.screen, bg, (x, y, w, h), border_radius=6)
        
        # Team accent
        color = Theme.CT if p['team'] == 'CT' else Theme.T
        if not alive:
            color = (color[0]//3, color[1]//3, color[2]//3)
        pygame.draw.rect(self.screen, color, (x, y + 6, 3, h - 12), border_radius=2)
        
        # Avatar with team color
        pygame.draw.circle(self.screen, color, (x + 26, y + h//2), 14)
        pygame.draw.circle(self.screen, Theme.WHITE if alive else Theme.MUTED, (x + 26, y + h//2), 14, 2)
        
        # Bomb/Defuser indicators
        if p.get('bomb'):
            # Pulsing bomb indicator
            pulse = abs(math.sin(self.frame * 0.15)) * 5
            pygame.draw.circle(self.screen, Theme.BOMB_GLOW, (x + 26, y + h//2), int(6 + pulse))
            pygame.draw.circle(self.screen, Theme.DANGER, (x + 26, y + h//2), 5)
        if p.get('defuser'):
            pygame.draw.rect(self.screen, Theme.SUCCESS, (x + 36, y + 6, 10, 10), border_radius=2)
            self.screen.blit(self.font_xs.render("D", True, Theme.WHITE), (x + 39, y + 6))
        
        # Name
        name_color = Theme.WHITE if alive else Theme.MUTED
        self.screen.blit(self.font_md.render(p['name'], True, name_color), (x + 48, y + 6))
        
        if alive:
            # HP bar
            bar_x, bar_y, bar_w = x + 48, y + 28, 110
            pygame.draw.rect(self.screen, Theme.MUTED, (bar_x, bar_y, bar_w, 6), border_radius=3)
            
            hp = p['hp']
            hp_color = Theme.SUCCESS if hp > 50 else Theme.WARNING if hp > 25 else Theme.DANGER
            hp_w = int(bar_w * hp / 100)
            pygame.draw.rect(self.screen, hp_color, (bar_x, bar_y, hp_w, 6), border_radius=3)
            
            # Stats line
            stats = f"{hp}  |  {p['armor']}  |  ${p['equip']}"
            self.screen.blit(self.font_xs.render(stats, True, Theme.GRAY), (x + 48, y + 38))
            
            # Weapon
            weapon = p.get('weapon', '').replace('weapon_', '')[:10]
            if weapon:
                w_txt = self.font_xs.render(weapon, True, Theme.MUTED)
                self.screen.blit(w_txt, (x + w - w_txt.get_width() - 10, y + 18))
            
            # K/D
            kd = f"{p.get('kills', 0)}/{p.get('deaths', 0)}"
            self.screen.blit(self.font_sm.render(kd, True, Theme.GRAY), (x + w - 40, y + 6))
        else:
            self.screen.blit(self.font_sm.render("✕ ELIMINATED", True, Theme.DANGER), (x + 48, y + 28))
    
    def _draw_radar(self, players, tick):
        rx, ry = 375, 115
        
        # Panel background
        pygame.draw.rect(self.screen, Theme.PANEL, (rx - 10, ry - 10, self.radar_size + 20, self.radar_size + 20), border_radius=8)
        
        # Map image
        if self.map_scaled:
            self.screen.blit(self.map_scaled, (rx, ry))
        else:
            pygame.draw.rect(self.screen, Theme.CARD, (rx, ry, self.radar_size, self.radar_size))
            # Grid
            for i in range(0, self.radar_size, 50):
                pygame.draw.line(self.screen, Theme.BORDER, (rx + i, ry), (rx + i, ry + self.radar_size), 1)
                pygame.draw.line(self.screen, Theme.BORDER, (rx, ry + i), (rx + self.radar_size, ry + i), 1)
        
        # Utility
        self._draw_utility(rx, ry, tick)
        
        # Kill animations
        self._draw_kill_animations(rx, ry, tick)
        
        # Dead players
        for p in players:
            if not p['alive']:
                self._draw_dead_marker(p, rx, ry)
        
        # Alive players
        for p in players:
            if p['alive']:
                self._draw_player_dot(p, rx, ry)
        
        # Border
        pygame.draw.rect(self.screen, Theme.BORDER, (rx - 10, ry - 10, self.radar_size + 20, self.radar_size + 20), 2, border_radius=8)
    
    def _draw_utility(self, rx, ry, tick):
        scale = self.radar_size / 1024
        
        # Smokes with animated edges
        for s in self.smokes:
            if s['start'] <= tick <= s['end']:
                px, py = self.map_config.world_to_radar(s['x'], s['y'], 1024)
                x, y = rx + int(px * scale), ry + int(py * scale)
                
                # Animated smoke cloud
                offset = math.sin(self.frame * 0.08 + s['x'] * 0.01) * 3
                r = int(26 + offset)
                
                surf = pygame.Surface((r*2 + 16, r*2 + 16), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*Theme.SMOKE, 130), (r + 8, r + 8), r)
                pygame.draw.circle(surf, (*Theme.SMOKE, 80), (r + 8, r + 8), r - 10)
                self.screen.blit(surf, (x - r - 8, y - r - 8))
        
        # Mollies with flickering
        for m in self.mollies:
            if m['start'] <= tick <= m['end']:
                px, py = self.map_config.world_to_radar(m['x'], m['y'], 1024)
                x, y = rx + int(px * scale), ry + int(py * scale)
                
                flicker = int(abs(math.sin(self.frame * 0.25 + m['x'] * 0.01)) * 50)
                surf = pygame.Surface((56, 56), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 90 + flicker, 25, 170), (28, 28), 24)
                pygame.draw.circle(surf, (255, 180, 80, 100), (28, 28), 14)
                self.screen.blit(surf, (x - 28, y - 28))
        
        # Flashes with expanding ring
        for f in self.flashes:
            if f['start'] <= tick <= f['end']:
                px, py = self.map_config.world_to_radar(f['x'], f['y'], 1024)
                x, y = rx + int(px * scale), ry + int(py * scale)
                
                progress = (tick - f['start']) / 40
                r = int(15 + progress * 30)
                alpha = int(220 * (1 - progress))
                
                surf = pygame.Surface((r*2 + 16, r*2 + 16), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*Theme.FLASH, alpha), (r + 8, r + 8), r)
                pygame.draw.circle(surf, (255, 255, 255, alpha//2), (r + 8, r + 8), r//2)
                self.screen.blit(surf, (x - r - 8, y - r - 8))
        
        # HE with explosion effect
        for h in self.he_nades:
            if h['start'] <= tick <= h['end']:
                px, py = self.map_config.world_to_radar(h['x'], h['y'], 1024)
                x, y = rx + int(px * scale), ry + int(py * scale)
                
                progress = (tick - h['start']) / 30
                r = int(20 + progress * 20)
                alpha = int(200 * (1 - progress))
                
                surf = pygame.Surface((r*2 + 16, r*2 + 16), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*Theme.HE, alpha), (r + 8, r + 8), r)
                pygame.draw.circle(surf, (255, 200, 100, alpha), (r + 8, r + 8), int(r * 0.5))
                self.screen.blit(surf, (x - r - 8, y - r - 8))
    
    def _draw_kill_animations(self, rx, ry, tick):
        scale = self.radar_size / 1024
        
        for anim in self.kill_animations:
            px, py = self.map_config.world_to_radar(anim['x'], anim['y'], 1024)
            x, y = rx + int(px * scale), ry + int(py * scale)
            
            progress = (tick - anim['tick']) / 64
            r = int(20 + progress * 30)
            alpha = int(180 * (1 - progress))
            
            # Skull/death indicator
            color = (255, 80, 80, alpha) if anim['hs'] else (255, 150, 150, alpha)
            surf = pygame.Surface((r*2 + 10, r*2 + 10), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (r + 5, r + 5), 3)
            for i in range(4):
                angle = i * math.pi / 2
                lx = r + 5 + int(math.cos(angle) * (r * 0.7))
                ly = r + 5 + int(math.sin(angle) * (r * 0.7))
                pygame.draw.line(surf, color, (r + 5, r + 5), (lx, ly), 2)
            self.screen.blit(surf, (x - r - 5, y - r - 5))
    
    def _draw_player_dot(self, p, rx, ry):
        scale = self.radar_size / 1024
        px, py = self.map_config.world_to_radar(p['x'], p['y'], 1024)
        x, y = rx + int(px * scale), ry + int(py * scale)
        
        color = Theme.CT if p['team'] == 'CT' else Theme.T
        light = Theme.CT_LIGHT if p['team'] == 'CT' else Theme.T_LIGHT
        
        # Low HP warning pulse
        if p['hp'] < 30:
            pulse = abs(math.sin(self.frame * 0.12)) * 8
            pygame.draw.circle(self.screen, Theme.DANGER, (x, y), int(16 + pulse))
        
        # Outer glow
        pygame.draw.circle(self.screen, (*color, 100), (x, y), 14)
        
        # Main dot
        pygame.draw.circle(self.screen, color, (x, y), 10)
        pygame.draw.circle(self.screen, light, (x, y), 10, 2)
        
        # Bomb carrier - pulsing
        if p.get('bomb'):
            pulse = abs(math.sin(self.frame * 0.15)) * 4
            pygame.draw.circle(self.screen, Theme.BOMB_GLOW, (x, y), int(5 + pulse))
        
        # Defuser icon
        if p.get('defuser'):
            pygame.draw.circle(self.screen, Theme.SUCCESS, (x + 10, y - 10), 5)
        
        # Name label
        name = self.font_xs.render(p['name'][:7], True, Theme.WHITE)
        # Shadow
        shadow = self.font_xs.render(p['name'][:7], True, (0, 0, 0))
        self.screen.blit(shadow, (x - name.get_width()//2 + 1, y + 13))
        self.screen.blit(name, (x - name.get_width()//2, y + 12))
    
    def _draw_dead_marker(self, p, rx, ry):
        scale = self.radar_size / 1024
        px, py = self.map_config.world_to_radar(p['x'], p['y'], 1024)
        x, y = rx + int(px * scale), ry + int(py * scale)
        
        color = Theme.CT_DARK if p['team'] == 'CT' else Theme.T_DARK
        
        # X mark
        pygame.draw.line(self.screen, color, (x - 5, y - 5), (x + 5, y + 5), 2)
        pygame.draw.line(self.screen, color, (x + 5, y - 5), (x - 5, y + 5), 2)
    
    def _draw_killfeed(self):
        from src.intelligence.death_analyzer import DeathAnalyzer
        
        kx, ky = self.width - 285, 115
        kw = 270
        
        pygame.draw.rect(self.screen, Theme.PANEL, (kx - 5, ky - 5, kw + 10, 180), border_radius=6)
        self.screen.blit(self.font_sm.render("KILL FEED", True, Theme.GRAY), (kx, ky))
        
        ky += 20
        for i, k in enumerate(self.recent_kills[-5:]):
            y = ky + i * 30
            
            # Kill row background
            pygame.draw.rect(self.screen, (0, 0, 0, 120), (kx, y, kw, 28), border_radius=3)
            
            # Attacker
            kc = Theme.CT if k['attacker_team'] == 'CT' else Theme.T
            self.screen.blit(self.font_sm.render(k['attacker'][:8], True, kc), (kx + 5, y + 2))
            
            # Weapon + HS
            hs = "HS" if k['hs'] else ""
            weapon = f"[{k['weapon'][:6]}]{hs}"
            self.screen.blit(self.font_xs.render(weapon, True, Theme.MUTED), (kx + 80, y + 4))
            
            # Victim
            vc = Theme.CT if k.get('victim_team', 'T') == 'CT' else Theme.T
            self.screen.blit(self.font_sm.render(k['victim'][:8], True, Theme.DANGER), (kx + 155, y + 2))
            
            # Death reason - find matching analysis
            reason = ""
            if self.death_analyzer:
                for analysis in self.death_analyzer.round_deaths:
                    if analysis.victim_name == k['victim']:
                        primary = analysis.primary_mistake()
                        label = DeathAnalyzer.get_mistake_label(primary)
                        color = DeathAnalyzer.get_mistake_color(primary)
                        self.screen.blit(self.font_xs.render(label, True, color), (kx + 5, y + 15))
                        break
    
    def _draw_round_stats(self, players):
        sx, sy = self.width - 295, 310
        sw, sh = 280, 180  # Reduced height
        
        pygame.draw.rect(self.screen, Theme.PANEL, (sx - 5, sy, sw + 10, sh), border_radius=6)
        
        # Header
        self.screen.blit(self.font_lg.render("LIVE STATISTICS", True, Theme.ACCENT), (sx + 5, sy + 8))
        pygame.draw.line(self.screen, Theme.BORDER, (sx, sy + 34), (sx + sw, sy + 34), 1)
        
        cy = sy + 42
        
        # Round Kills
        self.screen.blit(self.font_md.render("Round Kills", True, Theme.WHITE), (sx + 5, cy))
        ct_k = str(self.round_kills.get('CT', 0))
        t_k = str(self.round_kills.get('T', 0))
        self.screen.blit(self.font_lg.render(ct_k, True, Theme.CT), (sx + 140, cy - 2))
        self.screen.blit(self.font_md.render(":", True, Theme.GRAY), (sx + 170, cy))
        self.screen.blit(self.font_lg.render(t_k, True, Theme.T), (sx + 190, cy - 2))
        cy += 28
        
        # Team HP with bars
        ct_hp = sum(p['hp'] for p in players if p['team'] == 'CT' and p['alive'])
        t_hp = sum(p['hp'] for p in players if p['team'] == 'T' and p['alive'])
        self.screen.blit(self.font_md.render("Team HP", True, Theme.WHITE), (sx + 5, cy))
        self.screen.blit(self.font_md.render(str(ct_hp), True, Theme.CT), (sx + 140, cy))
        self.screen.blit(self.font_md.render(":", True, Theme.GRAY), (sx + 170, cy))
        self.screen.blit(self.font_md.render(str(t_hp), True, Theme.T), (sx + 190, cy))
        cy += 28
        
        # Equipment
        ct_eq = sum(p['equip'] for p in players if p['team'] == 'CT' and p['alive'])
        t_eq = sum(p['equip'] for p in players if p['team'] == 'T' and p['alive'])
        self.screen.blit(self.font_md.render("Equipment", True, Theme.WHITE), (sx + 5, cy))
        self.screen.blit(self.font_sm.render(f"${ct_eq}", True, Theme.CT), (sx + 130, cy + 2))
        self.screen.blit(self.font_sm.render(f"${t_eq}", True, Theme.T), (sx + 200, cy + 2))
        cy += 28
        
        # Active Utility
        tick = self.all_ticks[self.tick_idx] if self.all_ticks else 0
        active_smokes = sum(1 for s in self.smokes if s['start'] <= tick <= s['end'])
        active_mollies = sum(1 for m in self.mollies if m['start'] <= tick <= m['end'])
        
        self.screen.blit(self.font_md.render("Active Utility", True, Theme.ACCENT2), (sx + 5, cy))
        pygame.draw.circle(self.screen, Theme.SMOKE, (sx + 140, cy + 8), 6)
        self.screen.blit(self.font_sm.render(f"{active_smokes}", True, Theme.WHITE), (sx + 152, cy + 2))
        pygame.draw.circle(self.screen, Theme.FIRE, (sx + 185, cy + 8), 6)
        self.screen.blit(self.font_sm.render(f"{active_mollies}", True, Theme.WHITE), (sx + 197, cy + 2))
    
    def _draw_timeline(self, tick):
        ty = self.height - 48
        tx, tw = 380, self.width - 420
        
        # Background
        pygame.draw.rect(self.screen, Theme.PANEL, (tx - 18, ty - 10, tw + 36, 36), border_radius=8)
        pygame. draw.rect(self.screen, Theme.CARD, (tx, ty, tw, 18), border_radius=4)
        
        if self.all_ticks:
            total = len(self.all_ticks) - 1
            if total > 0:
                prog = self.tick_idx / total
                pw = int(tw * prog)
                
                # Progress bar with gradient-like appearance
                pygame.draw.rect(self.screen, Theme.ACCENT, (tx, ty, pw, 18), border_radius=4)
                
                # Playhead
                pygame.draw.circle(self.screen, Theme.WHITE, (tx + pw, ty + 9), 10)
                pygame.draw.circle(self.screen, Theme.ACCENT, (tx + pw, ty + 9), 6)
                
                # Round markers
                max_tick = self.all_ticks[-1]
                for s, e, n in self.rounds:
                    if s < max_tick:
                        rx = tx + int((s / max_tick) * tw)
                        pygame.draw.line(self.screen, Theme.MUTED, (rx, ty - 5), (rx, ty + 3), 1)
                
                # Time
                secs = tick // 64
                mins, secs = secs // 60, secs % 60
                t_str = f"{mins}:{secs:02d}"
                self.screen.blit(self.font_md.render(t_str, True, Theme.WHITE), (tx - 55, ty - 1))
                
                # Duration
                total_secs = self.all_ticks[-1] // 64
                dur = f"{total_secs // 60}:{total_secs % 60:02d}"
                self.screen.blit(self.font_sm.render(dur, True, Theme.MUTED), (tx + tw + 8, ty + 1))
    
    def _draw_death_popups(self, tick):
        """Draw death analysis popups on the radar when deaths occur."""
        if not self.death_popups:
            return
        
        from src.intelligence.death_analyzer import DeathAnalyzer
        
        rx, ry = 375, 115
        scale = self.radar_size / 1024
        
        for analysis, expire_tick in self.death_popups:
            # Get position on radar
            px, py = self.map_config.world_to_radar(analysis.position[0], analysis.position[1], 1024)
            x, y = rx + int(px * scale), ry + int(py * scale)
            
            # Fade out effect
            time_left = expire_tick - tick
            alpha = min(255, int(time_left * 0.8))
            
            if analysis.mistakes:
                mistake = analysis.mistakes[0]
                color = DeathAnalyzer.get_mistake_color(mistake)
                
                # Draw larger popup box with full analytics
                box_w = 200
                box_h = 120
                box_x = min(x + 15, rx + self.radar_size - box_w - 10)
                box_y = max(y - box_h // 2, ry + 10)
                
                # Background
                surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
                pygame.draw.rect(surf, (20, 24, 32, min(230, alpha)), (0, 0, box_w, box_h), border_radius=8)
                pygame.draw.rect(surf, (*color, min(200, alpha)), (0, 0, 5, box_h), border_top_left_radius=8, border_bottom_left_radius=8)
                self.screen.blit(surf, (box_x, box_y))
                
                # Header - victim name + killer
                name_color = Theme.CT if analysis.victim_team == 'CT' else Theme.T
                self.screen.blit(self.font_md.render(f"{analysis.victim_name}", True, name_color), (box_x + 12, box_y + 6))
                self.screen.blit(self.font_xs.render(f"killed by {analysis.attacker_name}", True, Theme.MUTED), (box_x + 12, box_y + 24))
                
                # Severity badge
                sev_colors = [(100, 200, 100), (150, 200, 100), (255, 200, 50), (255, 120, 50), (255, 50, 50)]
                sev_color = sev_colors[min(analysis.severity - 1, 4)]
                pygame.draw.rect(self.screen, sev_color, (box_x + box_w - 28, box_y + 8, 22, 16), border_radius=4)
                self.screen.blit(self.font_sm.render(str(analysis.severity), True, (0, 0, 0)), (box_x + box_w - 21, box_y + 10))
                
                # Primary mistake label
                label = DeathAnalyzer.get_mistake_label(mistake)
                self.screen.blit(self.font_lg.render(label, True, color), (box_x + 12, box_y + 40))
                
                # Stats row 1: Teammates + Enemies
                cy = box_y + 65
                tm_dist = f"{int(analysis.teammate_distance)}u" if analysis.teammate_distance < 9000 else "ALONE"
                self.screen.blit(self.font_xs.render(f"Team: {tm_dist}", True, Theme.GRAY), (box_x + 12, cy))
                self.screen.blit(self.font_xs.render(f"vs {analysis.enemy_count} enemies", True, Theme.GRAY), (box_x + 110, cy))
                
                # Stats row 2: Trade + Blame
                cy += 16
                trade = "TRADED" if analysis.was_traded else "NOT TRADED"
                trade_color = Theme.SUCCESS if analysis.was_traded else Theme.DANGER
                self.screen.blit(self.font_xs.render(trade, True, trade_color), (box_x + 12, cy))
                
                blame = analysis.blame_score()
                blame_color = (100, 200, 100) if blame < 40 else (255, 180, 50) if blame < 60 else (255, 80, 80)
                self.screen.blit(self.font_xs.render(f"Blame: {blame:.0f}%", True, blame_color), (box_x + 110, cy))
                
                # Additional mistakes
                cy += 16
                if len(analysis.mistakes) > 1:
                    other = ", ".join([DeathAnalyzer.get_mistake_label(m) for m in analysis.mistakes[1:3]])
                    self.screen.blit(self.font_xs.render(f"+{other}", True, Theme.MUTED), (box_x + 12, cy))
                
                # Line to death position
                pygame.draw.line(self.screen, (*color, min(150, alpha)), (x, y), (box_x, box_y + box_h // 2), 2)
    
    def _draw_death_panel(self):
        """Draw the Live Rankings panel."""
        if not self.death_analyzer:
            return
        
        from src.intelligence.death_analyzer import DeathAnalyzer
        
        # Panel position - below stats panel
        px = self.width - 295
        py = 500
        pw = 280
        ph = 200
        
        pygame.draw.rect(self.screen, Theme.PANEL, (px - 5, py, pw + 10, ph), border_radius=6)
        
        # === LIVE RANKINGS ===
        self.screen.blit(self.font_lg.render("LIVE RANKINGS", True, Theme.ACCENT), (px + 5, py + 8))
        pygame.draw.line(self.screen, Theme.BORDER, (px, py + 34), (px + pw, py + 34), 1)
        
        rankings = self.death_analyzer.get_rankings()
        cy = py + 42
        
        # Show top 8 players
        for i, stats in enumerate(rankings[:8]):
            # Rank number
            self.screen.blit(self.font_sm.render(f"#{i+1}", True, Theme.MUTED), (px + 5, cy))
            
            # Grade badge
            grade = stats.rank_grade
            grade_color = DeathAnalyzer.get_grade_color(grade)
            pygame.draw.rect(self.screen, grade_color, (px + 28, cy + 1, 18, 14), border_radius=3)
            self.screen.blit(self.font_xs.render(grade, True, (0, 0, 0)), (px + 33, cy + 2))
            
            # Name
            name_color = Theme.CT if stats.team == 'CT' else Theme.T
            self.screen.blit(self.font_sm.render(stats.name[:9], True, name_color), (px + 50, cy))
            
            # K/D
            kd = f"{stats.kills}/{stats.deaths}"
            self.screen.blit(self.font_sm.render(kd, True, Theme.WHITE), (px + 140, cy))
            
            # Blame score
            blame = stats.avg_blame
            blame_color = (100, 200, 100) if blame < 40 else (255, 180, 50) if blame < 60 else (255, 80, 80)
            self.screen.blit(self.font_xs.render(f"{blame:.0f}%", True, blame_color), (px + 185, cy + 1))
            
            # Performance bar
            perf = min(100, stats.performance_score)
            bar_w = int(35 * perf / 100)
            pygame.draw.rect(self.screen, Theme.MUTED, (px + 220, cy + 3, 35, 8), border_radius=2)
            if bar_w > 0:
                pygame.draw.rect(self.screen, grade_color, (px + 220, cy + 3, bar_w, 8), border_radius=2)
            
            cy += 18

    def _draw_legend(self):
        ly = self.height - 22
        lx = 15
        
        # Utility legend - LARGER
        items = [
            (Theme.SMOKE, "Smoke"),
            (Theme.FIRE, "Fire"),
            (Theme.FLASH, "Flash"),
            (Theme.HE, "HE"),
        ]
        
        for color, label in items:
            pygame.draw.circle(self.screen, color, (lx + 10, ly), 10)
            txt = self.font_lg.render(label, True, Theme.WHITE)
            self.screen.blit(txt, (lx + 25, ly - 10))
            lx += txt.get_width() + 50
        
        # Controls hint - LARGER
        hint = "SPACE: Play  |  ←→: Seek  |  ↑↓: Speed  |  E/R: Round  |  F12: Screenshot  |  H: Help"
        self.screen.blit(self.font_md.render(hint, True, Theme.GRAY), (350, ly - 8))


def main():
    import argparse
    parser = argparse.ArgumentParser(description='SACRILEGE RADAR - CS2 Demo Viewer')
    parser.add_argument('demo', nargs='?', help='Demo file path')
    args = parser.parse_args()
    
    replayer = RadarReplayer(1500, 920)
    
    if args.demo:
        replayer.load_demo(Path(args.demo))
    else:
        demo_dir = Path(__file__).parent.parent / 'demo files'
        if demo_dir.exists():
            demos = list(demo_dir.glob('*.dem'))
            if demos:
                replayer.load_demo(demos[0])
    
    replayer.run()


if __name__ == '__main__':
    main()

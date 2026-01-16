"""
SACRILEGE RADAR - Professional CS2 Demo Replay Viewer
Enhanced native Python implementation with all utility effects
"""

import pygame
import sys
import math
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Team, Vector3


@dataclass
class MapConfig:
    """Map radar configuration from CS2 txt files."""
    name: str
    display_name: str
    pos_x: float
    pos_y: float
    scale: float
    
    def world_to_radar(self, world_x: float, world_y: float, img_size: int) -> tuple[int, int]:
        """Convert world coordinates to radar pixel coordinates."""
        px = (world_x - self.pos_x) / self.scale
        py = (self.pos_y - world_y) / self.scale
        px = max(0, min(img_size - 1, px))
        py = max(0, min(img_size - 1, py))
        return int(px), int(py)


MAP_CONFIGS = {
    'de_mirage': MapConfig('de_mirage', 'Mirage', -3230, 1713, 5.0),
    'de_dust2': MapConfig('de_dust2', 'Dust II', -2476, 3239, 4.4),
    'de_inferno': MapConfig('de_inferno', 'Inferno', -2087, 3870, 4.9),
    'de_ancient': MapConfig('de_ancient', 'Ancient', -2953, 2164, 5.0),
    'de_nuke': MapConfig('de_nuke', 'Nuke', -3453, 2887, 7.0),
    'de_overpass': MapConfig('de_overpass', 'Overpass', -4831, 1781, 5.2),
    'de_anubis': MapConfig('de_anubis', 'Anubis', -2796, 3328, 5.22),
    'de_vertigo': MapConfig('de_vertigo', 'Vertigo', -3168, 1762, 4.0),
    'de_train': MapConfig('de_train', 'Train', -2477, 2392, 4.7),
}


class Colors:
    """Premium color palette."""
    BG_DARK = (12, 14, 18)
    BG_PANEL = (18, 22, 28)
    BG_CARD = (25, 30, 38)
    BG_HEADER = (20, 24, 32)
    
    CT_PRIMARY = (92, 172, 238)
    CT_SECONDARY = (60, 130, 200)
    CT_GLOW = (120, 190, 255)
    
    T_PRIMARY = (232, 185, 75)
    T_SECONDARY = (180, 140, 50)
    T_GLOW = (255, 210, 100)
    
    ACCENT = (0, 200, 255)
    ACCENT_SECONDARY = (255, 85, 85)
    
    TEXT_WHITE = (240, 245, 250)
    TEXT_GRAY = (130, 140, 155)
    TEXT_MUTED = (80, 90, 105)
    
    HP_FULL = (80, 220, 120)
    HP_MED = (240, 180, 60)
    HP_LOW = (230, 70, 70)
    
    # Utility colors
    SMOKE = (200, 210, 220)
    FIRE = (255, 120, 40)
    FLASH = (255, 255, 200)
    HE = (255, 100, 100)
    BOMB = (255, 50, 50)


class RadarReplayer:
    """Professional CS2 radar replay viewer with full utility visualization."""
    
    def __init__(self, width: int = 1400, height: int = 900):
        pygame.init()
        pygame.font.init()
        
        self.width = width
        self.height = height
        self.radar_size = 680
        self.sidebar_width = 340
        
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("SACRILEGE RADAR")
        
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.font_title = pygame.font.SysFont('Helvetica', 26, bold=True)
        self.font_header = pygame.font.SysFont('Helvetica', 16, bold=True)
        self.font_body = pygame.font.SysFont('Helvetica', 13)
        self.font_small = pygame.font.SysFont('Helvetica', 11)
        self.font_tiny = pygame.font.SysFont('Helvetica', 9)
        
        # State
        self.demo_data = None
        self.map_config = None
        self.map_image = None
        self.map_image_scaled = None
        
        self.is_playing = False
        self.playback_speed = 1.0
        
        # Tick data
        self.tick_df: Optional[pd.DataFrame] = None
        self.all_ticks: list = []
        self.current_tick_idx = 0
        
        # Players
        self.players = {}
        
        # Rounds & Kills
        self.rounds = []
        self.kills_by_tick = {}
        self.current_round = 1
        
        # Utility - enhanced
        self.smokes = []      # Smoke grenades
        self.mollies = []     # Molotovs/Incendiaries
        self.flashes = []     # Flashbangs
        self.he_grenades = [] # HE Grenades
        
        # Recent kills for kill feed
        self.recent_kills = []
        
    def load_demo(self, demo_path: Path) -> bool:
        """Load demo and extract all data."""
        from demoparser2 import DemoParser as Demoparser2
        from src.parser.demo_parser import DemoParser
        
        print(f"Loading: {demo_path.name}")
        
        parser = DemoParser()
        result = parser.parse(demo_path)
        if not result.success:
            print(f"Parse error: {result.error}")
            return False
        
        self.demo_data = result.data
        map_name = self.demo_data.header.map_name
        self.map_config = MAP_CONFIGS.get(map_name, MAP_CONFIGS['de_mirage'])
        
        self._load_map_image(map_name)
        
        # Get player info
        for pid, pinfo in self.demo_data.players.items():
            self.players[pid] = {
                'name': pinfo.name,
                'team': pinfo.team.name,
            }
        
        # Get rounds and kills
        for rd in self.demo_data.rounds:
            self.rounds.append((rd.start_tick, rd.end_tick, rd.round_number))
            for kill in rd.kills:
                if kill.tick not in self.kills_by_tick:
                    self.kills_by_tick[kill.tick] = []
                
                attacker_name = self.players.get(kill.attacker_id, {}).get('name', '?')
                victim_name = self.players.get(kill.victim_id, {}).get('name', '?')
                attacker_team = self.players.get(kill.attacker_id, {}).get('team', 'CT')
                
                self.kills_by_tick[kill.tick].append({
                    'attacker_name': attacker_name,
                    'victim_name': victim_name,
                    'attacker_team': attacker_team,
                    'weapon': kill.weapon,
                    'headshot': kill.headshot,
                    'tick': kill.tick,
                })
        
        # Extract tick data
        print("Extracting player positions...")
        dp2 = Demoparser2(str(demo_path))
        
        tick_data = dp2.parse_ticks(["X", "Y", "Z", "yaw", "health", "is_alive", "has_bomb"])
        
        if isinstance(tick_data, pd.DataFrame):
            sample_rate = 4
            unique_ticks = sorted(tick_data['tick'].unique())
            sampled = unique_ticks[::sample_rate]
            self.tick_df = tick_data[tick_data['tick'].isin(sampled)]
            self.all_ticks = sorted(self.tick_df['tick'].unique())
        
        # Extract ALL utility events
        print("Extracting utility events...")
        
        # Smokes (18 second duration)
        try:
            data = dp2.parse_event("smokegrenade_detonate")
            if isinstance(data, pd.DataFrame):
                for _, row in data.iterrows():
                    self.smokes.append({
                        'x': float(row.get('x', 0)),
                        'y': float(row.get('y', 0)),
                        'start': int(row.get('tick', 0)),
                        'end': int(row.get('tick', 0)) + 1152,  # ~18 sec
                    })
        except: pass
        
        # Mollies (7 second duration)
        try:
            data = dp2.parse_event("inferno_startburn")
            if isinstance(data, pd.DataFrame):
                for _, row in data.iterrows():
                    self.mollies.append({
                        'x': float(row.get('x', 0)),
                        'y': float(row.get('y', 0)),
                        'start': int(row.get('tick', 0)),
                        'end': int(row.get('tick', 0)) + 448,  # ~7 sec
                    })
        except: pass
        
        # Flashbangs (0.5 second visual indicator)
        try:
            data = dp2.parse_event("flashbang_detonate")
            if isinstance(data, pd.DataFrame):
                for _, row in data.iterrows():
                    self.flashes.append({
                        'x': float(row.get('x', 0)),
                        'y': float(row.get('y', 0)),
                        'start': int(row.get('tick', 0)),
                        'end': int(row.get('tick', 0)) + 32,  # quick flash
                    })
        except: pass
        
        # HE Grenades (0.3 second explosion)
        try:
            data = dp2.parse_event("hegrenade_detonate")
            if isinstance(data, pd.DataFrame):
                for _, row in data.iterrows():
                    self.he_grenades.append({
                        'x': float(row.get('x', 0)),
                        'y': float(row.get('y', 0)),
                        'start': int(row.get('tick', 0)),
                        'end': int(row.get('tick', 0)) + 20,
                    })
        except: pass
        
        print(f"Map: {self.map_config.display_name}")
        print(f"Players: {len(self.players)}")
        print(f"Rounds: {len(self.rounds)}")
        print(f"Ticks: {len(self.all_ticks)}")
        print(f"Utility: {len(self.smokes)} smokes, {len(self.mollies)} fires, {len(self.flashes)} flashes, {len(self.he_grenades)} HEs")
        print("Ready!")
        
        return True
    
    def _load_map_image(self, map_name: str):
        """Load map overlay image."""
        maps_dir = Path(__file__).parent / 'maps'
        img_path = maps_dir / f"{map_name}.png"
        
        if img_path.exists():
            try:
                self.map_image = pygame.image.load(str(img_path))
                self.map_image_scaled = pygame.transform.smoothscale(
                    self.map_image, (self.radar_size, self.radar_size)
                )
                print(f"Loaded map: {img_path.name}")
            except Exception as e:
                print(f"Map load failed: {e}")
    
    def run(self):
        """Main game loop."""
        running = True
        last_update = pygame.time.get_ticks()
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_key(event)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_click(event)
                elif event.type == pygame.VIDEORESIZE:
                    self.width, self.height = event.w, event.h
                    self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
            
            # Playback
            if self.is_playing and self.all_ticks:
                now = pygame.time.get_ticks()
                if now - last_update > 30 / self.playback_speed:
                    self.current_tick_idx = min(self.current_tick_idx + 1, len(self.all_ticks) - 1)
                    last_update = now
                    self._update_state()
            
            self._render()
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
    
    def _update_state(self):
        """Update current round and kills."""
        if not self.all_ticks:
            return
        
        tick = self.all_ticks[self.current_tick_idx]
        
        # Find current round
        for start, end, rnum in self.rounds:
            if start <= tick <= end:
                if rnum != self.current_round:
                    self.current_round = rnum
                    self.recent_kills.clear()
                break
        
        # Update kill feed
        for ktick, kills in self.kills_by_tick.items():
            if tick - 320 < ktick <= tick:  # 5 second window
                for k in kills:
                    if k not in self.recent_kills:
                        self.recent_kills.append(k)
        
        self.recent_kills = [k for k in self.recent_kills if tick - k['tick'] < 320]
    
    def _handle_key(self, event):
        if event.key == pygame.K_SPACE:
            self.is_playing = not self.is_playing
        elif event.key == pygame.K_LEFT:
            self.current_tick_idx = max(0, self.current_tick_idx - 40)
            self._update_state()
        elif event.key == pygame.K_RIGHT:
            self.current_tick_idx = min(len(self.all_ticks) - 1, self.current_tick_idx + 40)
            self._update_state()
        elif event.key == pygame.K_UP:
            self.playback_speed = min(8.0, self.playback_speed * 2)
        elif event.key == pygame.K_DOWN:
            self.playback_speed = max(0.25, self.playback_speed / 2)
        elif event.key == pygame.K_r:
            self._next_round()
        elif event.key == pygame.K_e:
            self._prev_round()
    
    def _next_round(self):
        if not self.all_ticks:
            return
        tick = self.all_ticks[self.current_tick_idx]
        for start, end, rnum in self.rounds:
            if start > tick:
                for i, t in enumerate(self.all_ticks):
                    if t >= start:
                        self.current_tick_idx = i
                        self._update_state()
                        return
    
    def _prev_round(self):
        if not self.all_ticks:
            return
        tick = self.all_ticks[self.current_tick_idx]
        for start, end, rnum in reversed(self.rounds):
            if end < tick:
                for i, t in enumerate(self.all_ticks):
                    if t >= start:
                        self.current_tick_idx = i
                        self._update_state()
                        return
    
    def _handle_click(self, event):
        x, y = event.pos
        # Timeline click
        tl_y = self.height - 45
        tl_x = self.sidebar_width + 20
        tl_w = self.width - self.sidebar_width - 40
        
        if tl_y <= y <= tl_y + 20 and tl_x <= x <= tl_x + tl_w and self.all_ticks:
            progress = (x - tl_x) / tl_w
            self.current_tick_idx = int(progress * (len(self.all_ticks) - 1))
            self._update_state()
    
    def _get_players(self, tick: int) -> list:
        if self.tick_df is None:
            return []
        
        data = self.tick_df[self.tick_df['tick'] == tick]
        players = []
        
        for _, row in data.iterrows():
            sid = str(row.get('steamid', ''))
            if sid not in self.players:
                continue
            
            pinfo = self.players[sid]
            is_alive = bool(row.get('is_alive', True))
            health = int(row.get('health', 0))
            if health > 0:
                is_alive = True
            
            players.append({
                'id': sid,
                'name': pinfo['name'],
                'team': pinfo['team'],
                'x': float(row.get('X', 0)),
                'y': float(row.get('Y', 0)),
                'yaw': float(row.get('yaw', 0)),
                'health': health if is_alive else 0,
                'alive': is_alive,
                'has_bomb': bool(row.get('has_bomb', False)),
            })
        
        return players
    
    def _render(self):
        self.screen.fill(Colors.BG_DARK)
        
        if not self.all_ticks:
            txt = self.font_title.render("Loading demo...", True, Colors.TEXT_WHITE)
            self.screen.blit(txt, (self.width//2 - txt.get_width()//2, self.height//2))
            return
        
        tick = self.all_ticks[self.current_tick_idx]
        players = self._get_players(tick)
        
        self._draw_header()
        self._draw_sidebar(players)
        self._draw_radar(players, tick)
        self._draw_killfeed()
        self._draw_timeline()
        self._draw_legend()
    
    def _draw_header(self):
        pygame.draw.rect(self.screen, Colors.BG_HEADER, (0, 0, self.width, 50))
        
        # Logo
        logo = self.font_title.render("SACRILEGE", True, Colors.ACCENT)
        self.screen.blit(logo, (15, 10))
        
        # Separator
        pygame.draw.line(self.screen, Colors.ACCENT, (0, 49), (self.width, 49), 2)
        
        # Map name and round
        if self.map_config:
            info = f"{self.map_config.display_name}  •  Round {self.current_round}/{len(self.rounds)}"
            txt = self.font_header.render(info, True, Colors.TEXT_WHITE)
            self.screen.blit(txt, (self.width//2 - txt.get_width()//2, 15))
        
        # Playback state
        state_icon = "⏸" if self.is_playing else "▶"
        speed_txt = f"{state_icon}  {self.playback_speed}x"
        speed = self.font_body.render(speed_txt, True, Colors.ACCENT)
        self.screen.blit(speed, (self.width - speed.get_width() - 20, 16))
    
    def _draw_sidebar(self, players):
        sx, sy = 10, 60
        sw = self.sidebar_width - 20
        
        # CT Section
        pygame.draw.rect(self.screen, Colors.BG_PANEL, (sx, sy, sw, 28), border_radius=4)
        pygame.draw.line(self.screen, Colors.CT_PRIMARY, (sx, sy), (sx, sy + 28), 3)
        
        ct_alive = sum(1 for p in players if p['team'] == 'CT' and p['alive'])
        ct_txt = f"COUNTER-TERRORISTS  ({ct_alive}/5)"
        self.screen.blit(self.font_header.render(ct_txt, True, Colors.CT_PRIMARY), (sx + 10, sy + 5))
        
        cy = sy + 35
        for p in sorted(players, key=lambda x: (not x['alive'], x['name'])):
            if p['team'] == 'CT':
                self._draw_player_row(p, sx, cy, sw)
                cy += 48
        
        # T Section
        ty = cy + 12
        pygame.draw.rect(self.screen, Colors.BG_PANEL, (sx, ty, sw, 28), border_radius=4)
        pygame.draw.line(self.screen, Colors.T_PRIMARY, (sx, ty), (sx, ty + 28), 3)
        
        t_alive = sum(1 for p in players if p['team'] == 'T' and p['alive'])
        t_txt = f"TERRORISTS  ({t_alive}/5)"
        self.screen.blit(self.font_header.render(t_txt, True, Colors.T_PRIMARY), (sx + 10, ty + 5))
        
        ty += 35
        for p in sorted(players, key=lambda x: (not x['alive'], x['name'])):
            if p['team'] == 'T':
                self._draw_player_row(p, sx, ty, sw)
                ty += 48
    
    def _draw_player_row(self, p, x, y, w):
        h = 44
        bg = Colors.BG_CARD if p['alive'] else (20, 22, 26)
        pygame.draw.rect(self.screen, bg, (x, y, w, h), border_radius=5)
        
        color = Colors.CT_PRIMARY if p['team'] == 'CT' else Colors.T_PRIMARY
        if not p['alive']:
            color = (color[0]//3, color[1]//3, color[2]//3)
        
        pygame.draw.line(self.screen, color, (x, y + 5), (x, y + h - 5), 3)
        
        # Avatar circle
        pygame.draw.circle(self.screen, color, (x + 25, y + h//2), 12)
        
        # Bomb indicator
        if p.get('has_bomb'):
            pygame.draw.circle(self.screen, Colors.BOMB, (x + 25, y + h//2), 5)
        
        # Name
        name_color = Colors.TEXT_WHITE if p['alive'] else Colors.TEXT_MUTED
        self.screen.blit(self.font_body.render(p['name'], True, name_color), (x + 45, y + 6))
        
        if p['alive']:
            # Health bar
            bar_x, bar_y, bar_w, bar_h = x + 45, y + 28, 130, 5
            pygame.draw.rect(self.screen, (40, 45, 55), (bar_x, bar_y, bar_w, bar_h), border_radius=2)
            
            hp = p['health']
            hp_color = Colors.HP_FULL if hp > 50 else Colors.HP_MED if hp > 25 else Colors.HP_LOW
            hp_w = int(bar_w * hp / 100)
            pygame.draw.rect(self.screen, hp_color, (bar_x, bar_y, hp_w, bar_h), border_radius=2)
            
            self.screen.blit(self.font_tiny.render(f"{hp}", True, Colors.TEXT_GRAY), (bar_x + bar_w + 6, bar_y - 2))
        else:
            self.screen.blit(self.font_small.render("DEAD", True, Colors.HP_LOW), (x + 45, y + 26))
    
    def _draw_radar(self, players, tick):
        rx = self.sidebar_width + 10
        ry = 60
        
        # Background panel
        pygame.draw.rect(self.screen, Colors.BG_PANEL, (rx - 5, ry - 5, self.radar_size + 10, self.radar_size + 10), border_radius=6)
        
        # Map image
        if self.map_image_scaled:
            self.screen.blit(self.map_image_scaled, (rx, ry))
        else:
            pygame.draw.rect(self.screen, (25, 30, 40), (rx, ry, self.radar_size, self.radar_size))
        
        # Draw utility
        self._draw_all_utility(rx, ry, tick)
        
        # Draw dead players first
        for p in players:
            if not p['alive']:
                self._draw_dead_marker(p, rx, ry)
        
        # Draw alive players
        for p in players:
            if p['alive']:
                self._draw_player_marker(p, rx, ry)
        
        # Border
        pygame.draw.rect(self.screen, Colors.ACCENT, (rx - 5, ry - 5, self.radar_size + 10, self.radar_size + 10), 2, border_radius=6)
    
    def _draw_all_utility(self, rx, ry, tick):
        scale = self.radar_size / 1024
        
        # Smokes - gray cloud
        for s in self.smokes:
            if s['start'] <= tick <= s['end']:
                px, py = self.map_config.world_to_radar(s['x'], s['y'], 1024)
                x, y = rx + int(px * scale), ry + int(py * scale)
                
                surf = pygame.Surface((60, 60), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*Colors.SMOKE, 150), (30, 30), 28)
                pygame.draw.circle(surf, (*Colors.SMOKE, 100), (30, 30), 22)
                self.screen.blit(surf, (x - 30, y - 30))
        
        # Mollies - orange fire
        for m in self.mollies:
            if m['start'] <= tick <= m['end']:
                px, py = self.map_config.world_to_radar(m['x'], m['y'], 1024)
                x, y = rx + int(px * scale), ry + int(py * scale)
                
                surf = pygame.Surface((50, 50), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*Colors.FIRE, 180), (25, 25), 22)
                pygame.draw.circle(surf, (255, 200, 100, 120), (25, 25), 15)
                self.screen.blit(surf, (x - 25, y - 25))
        
        # Flashes - bright burst
        for f in self.flashes:
            if f['start'] <= tick <= f['end']:
                px, py = self.map_config.world_to_radar(f['x'], f['y'], 1024)
                x, y = rx + int(px * scale), ry + int(py * scale)
                
                surf = pygame.Surface((70, 70), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*Colors.FLASH, 200), (35, 35), 32)
                pygame.draw.circle(surf, (255, 255, 255, 150), (35, 35), 20)
                self.screen.blit(surf, (x - 35, y - 35))
        
        # HE Grenades - red explosion
        for h in self.he_grenades:
            if h['start'] <= tick <= h['end']:
                px, py = self.map_config.world_to_radar(h['x'], h['y'], 1024)
                x, y = rx + int(px * scale), ry + int(py * scale)
                
                surf = pygame.Surface((60, 60), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*Colors.HE, 180), (30, 30), 28)
                pygame.draw.circle(surf, (255, 200, 100, 150), (30, 30), 18)
                self.screen.blit(surf, (x - 30, y - 30))
    
    def _draw_player_marker(self, p, rx, ry):
        scale = self.radar_size / 1024
        px, py = self.map_config.world_to_radar(p['x'], p['y'], 1024)
        x, y = rx + int(px * scale), ry + int(py * scale)
        
        color = Colors.CT_PRIMARY if p['team'] == 'CT' else Colors.T_PRIMARY
        glow = Colors.CT_GLOW if p['team'] == 'CT' else Colors.T_GLOW
        
        # View cone
        yaw = math.radians(p['yaw'] - 90)
        cone_len = 32
        
        cone_surf = pygame.Surface((80, 80), pygame.SRCALPHA)
        pts = [
            (40, 40),
            (40 + int(math.cos(yaw - 0.35) * cone_len), 40 + int(math.sin(yaw - 0.35) * cone_len)),
            (40 + int(math.cos(yaw + 0.35) * cone_len), 40 + int(math.sin(yaw + 0.35) * cone_len)),
        ]
        pygame.draw.polygon(cone_surf, (*color, 80), pts)
        self.screen.blit(cone_surf, (x - 40, y - 40))
        
        # Glow
        pygame.draw.circle(self.screen, (*glow, 60), (x, y), 14)
        
        # Main dot
        pygame.draw.circle(self.screen, color, (x, y), 10)
        pygame.draw.circle(self.screen, Colors.TEXT_WHITE, (x, y), 10, 2)
        
        # Bomb indicator
        if p.get('has_bomb'):
            pygame.draw.circle(self.screen, Colors.BOMB, (x, y), 5)
        
        # Name label
        name = self.font_tiny.render(p['name'][:5], True, (30, 30, 40))
        self.screen.blit(name, (x - name.get_width()//2, y - 4))
    
    def _draw_dead_marker(self, p, rx, ry):
        scale = self.radar_size / 1024
        px, py = self.map_config.world_to_radar(p['x'], p['y'], 1024)
        x, y = rx + int(px * scale), ry + int(py * scale)
        
        color = Colors.CT_SECONDARY if p['team'] == 'CT' else Colors.T_SECONDARY
        
        pygame.draw.line(self.screen, color, (x - 5, y - 5), (x + 5, y + 5), 2)
        pygame.draw.line(self.screen, color, (x + 5, y - 5), (x - 5, y + 5), 2)
    
    def _draw_killfeed(self):
        kx = self.width - 270
        ky = 60
        
        for i, k in enumerate(self.recent_kills[-6:]):
            y = ky + i * 26
            
            # Background
            pygame.draw.rect(self.screen, (0, 0, 0, 200), (kx, y, 255, 22), border_radius=3)
            
            killer_color = Colors.CT_PRIMARY if k['attacker_team'] == 'CT' else Colors.T_PRIMARY
            self.screen.blit(self.font_small.render(k['attacker_name'][:8], True, killer_color), (kx + 5, y + 4))
            
            weapon_txt = f"[{k['weapon'][:8]}]"
            self.screen.blit(self.font_tiny.render(weapon_txt, True, Colors.TEXT_GRAY), (kx + 80, y + 5))
            
            hs = "●" if k['headshot'] else ""
            victim_txt = k['victim_name'][:8] + hs
            self.screen.blit(self.font_small.render(victim_txt, True, Colors.HP_LOW), (kx + 155, y + 4))
    
    def _draw_timeline(self):
        ty = self.height - 50
        tx = self.sidebar_width + 20
        tw = self.width - self.sidebar_width - 40
        th = 18
        
        pygame.draw.rect(self.screen, Colors.BG_PANEL, (tx - 10, ty - 5, tw + 20, th + 10), border_radius=5)
        pygame.draw.rect(self.screen, Colors.BG_CARD, (tx, ty, tw, th), border_radius=3)
        
        if self.all_ticks:
            progress = self.current_tick_idx / max(1, len(self.all_ticks) - 1)
            prog_w = int(tw * progress)
            
            pygame.draw.rect(self.screen, Colors.ACCENT, (tx, ty, prog_w, th), border_radius=3)
            
            # Playhead
            pygame.draw.circle(self.screen, Colors.TEXT_WHITE, (tx + prog_w, ty + th//2), 8)
            pygame.draw.circle(self.screen, Colors.ACCENT, (tx + prog_w, ty + th//2), 5)
            
            # Time
            tick = self.all_ticks[self.current_tick_idx]
            secs = tick // 64
            time_txt = f"{secs // 60}:{secs % 60:02d}"
            self.screen.blit(self.font_body.render(time_txt, True, Colors.TEXT_WHITE), (tx - 50, ty))
    
    def _draw_legend(self):
        ly = self.height - 25
        lx = 15
        
        items = [
            ("●", Colors.SMOKE, "Smoke"),
            ("●", Colors.FIRE, "Fire"),
            ("●", Colors.FLASH, "Flash"),
            ("●", Colors.HE, "HE"),
        ]
        
        for icon, color, label in items:
            pygame.draw.circle(self.screen, color, (lx + 5, ly + 5), 5)
            txt = self.font_tiny.render(label, True, Colors.TEXT_MUTED)
            self.screen.blit(txt, (lx + 15, ly))
            lx += txt.get_width() + 30
        
        # Controls hint
        hint = "SPACE: Play  ←→: Seek  ↑↓: Speed  E/R: Round"
        self.screen.blit(self.font_tiny.render(hint, True, Colors.TEXT_MUTED), (self.sidebar_width + 20, ly))


def main():
    import argparse
    parser = argparse.ArgumentParser(description='SACRILEGE RADAR')
    parser.add_argument('demo', nargs='?', help='Demo file')
    args = parser.parse_args()
    
    replayer = RadarReplayer(1400, 900)
    
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

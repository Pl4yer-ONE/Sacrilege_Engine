"""
SACRILEGE RADAR - Professional CS2 Demo Replay Viewer
Premium native Python implementation with real map overlays
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
    BG_DARK = (8, 10, 15)
    BG_PANEL = (15, 18, 25)
    BG_CARD = (22, 26, 35)
    BG_HOVER = (30, 35, 48)
    
    CT_PRIMARY = (77, 166, 255)
    CT_DARK = (45, 95, 150)
    CT_GLOW = (100, 180, 255)
    
    T_PRIMARY = (255, 200, 50)
    T_DARK = (150, 115, 30)
    T_GLOW = (255, 220, 100)
    
    ACCENT_CYAN = (0, 212, 255)
    ACCENT_MAGENTA = (255, 0, 170)
    ACCENT_GOLD = (255, 215, 0)
    
    TEXT_WHITE = (255, 255, 255)
    TEXT_GRAY = (140, 145, 160)
    TEXT_DARK = (80, 85, 100)
    
    HEALTH_HIGH = (68, 255, 136)
    HEALTH_MED = (255, 180, 50)
    HEALTH_LOW = (255, 68, 68)
    
    SMOKE = (180, 180, 180, 140)
    MOLLY = (255, 100, 30, 160)
    BOMB = (255, 50, 50)


class RadarReplayer:
    """Professional CS2 radar replay viewer."""
    
    def __init__(self, width: int = 1400, height: int = 900):
        pygame.init()
        pygame.font.init()
        
        self.width = width
        self.height = height
        self.radar_size = 700
        
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("SACRILEGE RADAR")
        
        self.clock = pygame.time.Clock()
        
        # Fonts
        try:
            self.font_title = pygame.font.SysFont('SF Pro Display', 28, bold=True)
            self.font_header = pygame.font.SysFont('SF Pro Display', 18, bold=True)
            self.font_body = pygame.font.SysFont('SF Pro Text', 14)
            self.font_small = pygame.font.SysFont('SF Pro Text', 11)
        except:
            self.font_title = pygame.font.SysFont('Arial', 28, bold=True)
            self.font_header = pygame.font.SysFont('Arial', 18, bold=True)
            self.font_body = pygame.font.SysFont('Arial', 14)
            self.font_small = pygame.font.SysFont('Arial', 11)
        
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
        self.dead_players = set()
        self.current_round = 1
        
        # Utility
        self.smokes = []
        self.mollies = []
        
        # Recent kills for kill feed
        self.recent_kills = []
        
        # UI state
        self.hovered_player = None
        
    def load_demo(self, demo_path: Path) -> bool:
        """Load demo and extract all tick data."""
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
        
        # Load map image
        self._load_map_image(map_name)
        
        # Get player info
        for pid, pinfo in self.demo_data.players.items():
            self.players[pid] = {
                'name': pinfo.name,
                'team': pinfo.team.name,
            }
        
        # Get round boundaries and kills
        for rd in self.demo_data.rounds:
            self.rounds.append((rd.start_tick, rd.end_tick, rd.round_number))
            for kill in rd.kills:
                if kill.tick not in self.kills_by_tick:
                    self.kills_by_tick[kill.tick] = []
                
                attacker_name = self.players.get(kill.attacker_id, {}).get('name', 'Unknown')
                victim_name = self.players.get(kill.victim_id, {}).get('name', 'Unknown')
                attacker_team = self.players.get(kill.attacker_id, {}).get('team', 'CT')
                
                self.kills_by_tick[kill.tick].append({
                    'attacker': kill.attacker_id,
                    'victim': kill.victim_id,
                    'attacker_name': attacker_name,
                    'victim_name': victim_name,
                    'attacker_team': attacker_team,
                    'weapon': kill.weapon,
                    'headshot': kill.headshot,
                    'tick': kill.tick,
                })
        
        # Load tick data
        print("Extracting positions...")
        dp2 = Demoparser2(str(demo_path))
        
        tick_data = dp2.parse_ticks(["X", "Y", "Z", "yaw", "health", "team_num", "is_alive"])
        
        if isinstance(tick_data, pd.DataFrame):
            sample_rate = 4
            unique_ticks = sorted(tick_data['tick'].unique())
            sampled_ticks = unique_ticks[::sample_rate]
            self.tick_df = tick_data[tick_data['tick'].isin(sampled_ticks)]
            self.all_ticks = sorted(self.tick_df['tick'].unique())
        
        # Extract utility
        try:
            smoke_data = dp2.parse_event("smokegrenade_detonate")
            if isinstance(smoke_data, pd.DataFrame):
                for _, row in smoke_data.iterrows():
                    self.smokes.append({
                        'x': float(row.get('x', 0)),
                        'y': float(row.get('y', 0)),
                        'start': int(row.get('tick', 0)),
                        'end': int(row.get('tick', 0)) + 1152,
                    })
        except:
            pass
        
        try:
            molly_data = dp2.parse_event("inferno_startburn")
            if isinstance(molly_data, pd.DataFrame):
                for _, row in molly_data.iterrows():
                    self.mollies.append({
                        'x': float(row.get('x', 0)),
                        'y': float(row.get('y', 0)),
                        'start': int(row.get('tick', 0)),
                        'end': int(row.get('tick', 0)) + 448,
                    })
        except:
            pass
        
        print(f"Map: {self.map_config.display_name}")
        print(f"Players: {len(self.players)}")
        print(f"Rounds: {len(self.rounds)}")
        print(f"Ticks: {len(self.all_ticks)}")
        print("Ready!")
        
        return True
    
    def _load_map_image(self, map_name: str):
        """Load and prepare map image."""
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
                print(f"Failed to load map: {e}")
                self.map_image = None
        else:
            print(f"Map image not found: {img_path}")
    
    def run(self):
        """Main game loop."""
        running = True
        last_update = pygame.time.get_ticks()
        
        while running:
            dt = self.clock.tick(60) / 1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_keydown(event)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_click(event)
                elif event.type == pygame.VIDEORESIZE:
                    self.width, self.height = event.w, event.h
                    self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
            
            # Playback
            if self.is_playing and self.all_ticks:
                now = pygame.time.get_ticks()
                frame_time = 32 / self.playback_speed
                if now - last_update > frame_time:
                    self.current_tick_idx = min(self.current_tick_idx + 1, len(self.all_ticks) - 1)
                    last_update = now
                    self._update_state()
            
            self._render()
            pygame.display.flip()
        
        pygame.quit()
    
    def _update_state(self):
        """Update game state for current tick."""
        if not self.all_ticks:
            return
        
        current_tick = self.all_ticks[self.current_tick_idx]
        
        # Update current round
        for start, end, rnum in self.rounds:
            if start <= current_tick <= end:
                if rnum != self.current_round:
                    self.current_round = rnum
                    self.dead_players.clear()
                    self.recent_kills.clear()
                break
        
        # Find round start
        round_start = 0
        for start, end, rnum in self.rounds:
            if rnum == self.current_round:
                round_start = start
                break
        
        # Update deaths and kill feed
        for tick, kills in self.kills_by_tick.items():
            if round_start <= tick <= current_tick:
                for kill in kills:
                    self.dead_players.add(kill['victim'])
                    # Add to recent kills if within 5 seconds
                    if current_tick - tick < 320:
                        if kill not in self.recent_kills:
                            self.recent_kills.append(kill)
        
        # Trim old kills from feed
        self.recent_kills = [k for k in self.recent_kills if current_tick - k['tick'] < 320]
    
    def _handle_keydown(self, event):
        if event.key == pygame.K_SPACE:
            self.is_playing = not self.is_playing
        elif event.key == pygame.K_LEFT:
            self.current_tick_idx = max(0, self.current_tick_idx - 30)
            self._update_state()
        elif event.key == pygame.K_RIGHT:
            self.current_tick_idx = min(len(self.all_ticks) - 1, self.current_tick_idx + 30)
            self._update_state()
        elif event.key == pygame.K_UP:
            self.playback_speed = min(8.0, self.playback_speed * 2)
        elif event.key == pygame.K_DOWN:
            self.playback_speed = max(0.25, self.playback_speed / 2)
        elif event.key == pygame.K_r:
            self._goto_next_round()
        elif event.key == pygame.K_e:
            self._goto_prev_round()
        elif event.key == pygame.K_HOME:
            self.current_tick_idx = 0
            self._update_state()
        elif event.key == pygame.K_END:
            self.current_tick_idx = len(self.all_ticks) - 1
            self._update_state()
    
    def _goto_next_round(self):
        if not self.all_ticks:
            return
        current_tick = self.all_ticks[self.current_tick_idx]
        for start, end, rnum in self.rounds:
            if start > current_tick:
                for i, t in enumerate(self.all_ticks):
                    if t >= start:
                        self.current_tick_idx = i
                        self._update_state()
                        return
    
    def _goto_prev_round(self):
        if not self.all_ticks:
            return
        current_tick = self.all_ticks[self.current_tick_idx]
        for start, end, rnum in reversed(self.rounds):
            if end < current_tick:
                for i, t in enumerate(self.all_ticks):
                    if t >= start:
                        self.current_tick_idx = i
                        self._update_state()
                        return
    
    def _handle_click(self, event):
        x, y = event.pos
        tl_y = self.height - 50
        tl_x, tl_w = 350, self.width - 380
        
        if tl_y <= y <= tl_y + 20 and tl_x <= x <= tl_x + tl_w and self.all_ticks:
            progress = (x - tl_x) / tl_w
            self.current_tick_idx = int(progress * (len(self.all_ticks) - 1))
            self._update_state()
    
    def _get_players_at_tick(self, tick: int) -> list:
        if self.tick_df is None:
            return []
        
        tick_data = self.tick_df[self.tick_df['tick'] == tick]
        players = []
        
        for _, row in tick_data.iterrows():
            steamid = str(row.get('steamid', ''))
            if steamid not in self.players:
                continue
            
            pinfo = self.players[steamid]
            
            # Use is_alive from tick data directly
            is_alive = bool(row.get('is_alive', True))
            health = int(row.get('health', 0))
            
            # Double check: if health > 0, player is alive
            if health > 0:
                is_alive = True
            
            players.append({
                'id': steamid,
                'name': pinfo['name'],
                'team': pinfo['team'],
                'x': float(row.get('X', 0)),
                'y': float(row.get('Y', 0)),
                'z': float(row.get('Z', 0)),
                'yaw': float(row.get('yaw', 0)),
                'health': health if is_alive else 0,
                'alive': is_alive,
            })
        
        return players
    
    def _render(self):
        self.screen.fill(Colors.BG_DARK)
        
        if not self.all_ticks:
            self._render_no_data()
            return
        
        current_tick = self.all_ticks[self.current_tick_idx]
        players = self._get_players_at_tick(current_tick)
        
        self._render_header()
        self._render_sidebar(players)
        self._render_radar(players, current_tick)
        self._render_kill_feed()
        self._render_timeline()
        self._render_controls_hint()
    
    def _render_no_data(self):
        text = self.font_title.render("Drop a .dem file to start", True, Colors.TEXT_WHITE)
        hint = self.font_body.render("Or run: python radar_replayer.py <demo.dem>", True, Colors.TEXT_GRAY)
        self.screen.blit(text, (self.width//2 - text.get_width()//2, self.height//2 - 30))
        self.screen.blit(hint, (self.width//2 - hint.get_width()//2, self.height//2 + 10))
    
    def _render_header(self):
        # Header background
        pygame.draw.rect(self.screen, Colors.BG_PANEL, (0, 0, self.width, 55))
        pygame.draw.line(self.screen, Colors.ACCENT_CYAN, (0, 55), (self.width, 55), 2)
        
        # Logo
        logo = self.font_title.render("SACRILEGE", True, Colors.ACCENT_CYAN)
        self.screen.blit(logo, (20, 12))
        
        # Map & Round
        if self.map_config:
            info = f"{self.map_config.display_name}"
            text = self.font_header.render(info, True, Colors.TEXT_WHITE)
            self.screen.blit(text, (self.width//2 - text.get_width()//2, 8))
            
            round_text = f"Round {self.current_round} / {len(self.rounds)}"
            rt = self.font_body.render(round_text, True, Colors.TEXT_GRAY)
            self.screen.blit(rt, (self.width//2 - rt.get_width()//2, 32))
        
        # Speed
        speed = self.font_small.render(f"{self.playback_speed}x", True, Colors.ACCENT_GOLD)
        self.screen.blit(speed, (self.width - 50, 20))
        
        # Play state
        state = "▶" if not self.is_playing else "⏸"
        state_text = self.font_header.render(state, True, Colors.ACCENT_CYAN)
        self.screen.blit(state_text, (self.width - 100, 15))
    
    def _render_sidebar(self, players):
        sx, sy = 10, 70
        sw = 320
        
        # CT section
        pygame.draw.rect(self.screen, Colors.BG_PANEL, (sx, sy, sw, 30), border_radius=5)
        pygame.draw.rect(self.screen, Colors.CT_PRIMARY, (sx, sy, 4, 30))
        ct_label = self.font_header.render("COUNTER-TERRORISTS", True, Colors.CT_PRIMARY)
        self.screen.blit(ct_label, (sx + 15, sy + 5))
        
        cy = sy + 35
        ct_alive = sum(1 for p in players if p['team'] == 'CT' and p['alive'])
        
        for p in sorted(players, key=lambda x: (not x['alive'], x['name'])):
            if p['team'] == 'CT':
                self._draw_player_card(p, sx, cy, sw)
                cy += 52
        
        # T section
        ty = cy + 15
        pygame.draw.rect(self.screen, Colors.BG_PANEL, (sx, ty, sw, 30), border_radius=5)
        pygame.draw.rect(self.screen, Colors.T_PRIMARY, (sx, ty, 4, 30))
        t_label = self.font_header.render("TERRORISTS", True, Colors.T_PRIMARY)
        self.screen.blit(t_label, (sx + 15, ty + 5))
        
        ty += 35
        for p in sorted(players, key=lambda x: (not x['alive'], x['name'])):
            if p['team'] == 'T':
                self._draw_player_card(p, sx, ty, sw)
                ty += 52
    
    def _draw_player_card(self, p, x, y, w):
        h = 48
        
        # Background
        bg = Colors.BG_CARD if p['alive'] else (18, 18, 22)
        pygame.draw.rect(self.screen, bg, (x, y, w, h), border_radius=6)
        
        # Team indicator
        color = Colors.CT_PRIMARY if p['team'] == 'CT' else Colors.T_PRIMARY
        if not p['alive']:
            color = (color[0]//3, color[1]//3, color[2]//3)
        pygame.draw.rect(self.screen, color, (x, y, 4, h), border_top_left_radius=6, border_bottom_left_radius=6)
        
        # Player icon
        icon_x = x + 20
        icon_y = y + h//2
        pygame.draw.circle(self.screen, color, (icon_x, icon_y), 14)
        if p['alive']:
            pygame.draw.circle(self.screen, Colors.TEXT_WHITE, (icon_x, icon_y), 14, 2)
        
        # Name
        name_color = Colors.TEXT_WHITE if p['alive'] else Colors.TEXT_DARK
        name = self.font_body.render(p['name'], True, name_color)
        self.screen.blit(name, (x + 45, y + 8))
        
        # Health bar or DEAD
        if p['alive']:
            bar_x, bar_y = x + 45, y + 30
            bar_w, bar_h = 160, 6
            
            pygame.draw.rect(self.screen, (30, 32, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
            
            hp = p['health']
            hp_color = Colors.HEALTH_HIGH if hp > 50 else Colors.HEALTH_MED if hp > 25 else Colors.HEALTH_LOW
            hp_width = int(bar_w * hp / 100)
            pygame.draw.rect(self.screen, hp_color, (bar_x, bar_y, hp_width, bar_h), border_radius=3)
            
            hp_text = self.font_small.render(f"{hp}", True, Colors.TEXT_GRAY)
            self.screen.blit(hp_text, (bar_x + bar_w + 8, bar_y - 2))
        else:
            dead = self.font_small.render("ELIMINATED", True, Colors.HEALTH_LOW)
            self.screen.blit(dead, (x + 45, y + 28))
    
    def _render_radar(self, players, current_tick):
        rx = 350
        ry = 70
        
        # Radar background
        pygame.draw.rect(self.screen, Colors.BG_PANEL, (rx - 10, ry - 10, self.radar_size + 20, self.radar_size + 20), border_radius=8)
        
        # Map image or grid
        if self.map_image_scaled:
            self.screen.blit(self.map_image_scaled, (rx, ry))
        else:
            pygame.draw.rect(self.screen, (20, 25, 35), (rx, ry, self.radar_size, self.radar_size))
            step = self.radar_size // 12
            for i in range(13):
                pygame.draw.line(self.screen, (35, 40, 50), (rx + i*step, ry), (rx + i*step, ry + self.radar_size))
                pygame.draw.line(self.screen, (35, 40, 50), (rx, ry + i*step), (rx + self.radar_size, ry + i*step))
        
        # Utility
        self._draw_utility(rx, ry, current_tick)
        
        # Players
        for p in players:
            if not p['alive']:
                self._draw_dead_player(p, rx, ry)
        for p in players:
            if p['alive']:
                self._draw_player(p, rx, ry)
        
        # Border
        pygame.draw.rect(self.screen, Colors.ACCENT_CYAN, (rx - 10, ry - 10, self.radar_size + 20, self.radar_size + 20), 2, border_radius=8)
    
    def _draw_utility(self, rx, ry, current_tick):
        # Smokes
        for smoke in self.smokes:
            if smoke['start'] <= current_tick <= smoke['end']:
                px, py = self.map_config.world_to_radar(smoke['x'], smoke['y'], 1024)
                x = rx + int(px * self.radar_size / 1024)
                y = ry + int(py * self.radar_size / 1024)
                
                surf = pygame.Surface((70, 70), pygame.SRCALPHA)
                pygame.draw.circle(surf, Colors.SMOKE, (35, 35), 32)
                self.screen.blit(surf, (x - 35, y - 35))
        
        # Mollies
        for molly in self.mollies:
            if molly['start'] <= current_tick <= molly['end']:
                px, py = self.map_config.world_to_radar(molly['x'], molly['y'], 1024)
                x = rx + int(px * self.radar_size / 1024)
                y = ry + int(py * self.radar_size / 1024)
                
                surf = pygame.Surface((50, 50), pygame.SRCALPHA)
                pygame.draw.circle(surf, Colors.MOLLY, (25, 25), 22)
                self.screen.blit(surf, (x - 25, y - 25))
    
    def _draw_player(self, p, rx, ry):
        px, py = self.map_config.world_to_radar(p['x'], p['y'], 1024)
        x = rx + int(px * self.radar_size / 1024)
        y = ry + int(py * self.radar_size / 1024)
        
        color = Colors.CT_PRIMARY if p['team'] == 'CT' else Colors.T_PRIMARY
        glow = Colors.CT_GLOW if p['team'] == 'CT' else Colors.T_GLOW
        
        # View cone
        yaw = math.radians(p['yaw'] - 90)
        cone_len = 35
        
        cone_surf = pygame.Surface((90, 90), pygame.SRCALPHA)
        pts = [
            (45, 45),
            (45 + int(math.cos(yaw - 0.35) * cone_len), 45 + int(math.sin(yaw - 0.35) * cone_len)),
            (45 + int(math.cos(yaw + 0.35) * cone_len), 45 + int(math.sin(yaw + 0.35) * cone_len)),
        ]
        pygame.draw.polygon(cone_surf, (*color, 70), pts)
        self.screen.blit(cone_surf, (x - 45, y - 45))
        
        # Player dot with glow
        pygame.draw.circle(self.screen, (*glow, 80), (x, y), 16)
        pygame.draw.circle(self.screen, color, (x, y), 12)
        pygame.draw.circle(self.screen, Colors.TEXT_WHITE, (x, y), 12, 2)
        
        # Name
        name = self.font_small.render(p['name'][:5], True, (20, 20, 30))
        self.screen.blit(name, (x - name.get_width()//2, y - name.get_height()//2))
    
    def _draw_dead_player(self, p, rx, ry):
        px, py = self.map_config.world_to_radar(p['x'], p['y'], 1024)
        x = rx + int(px * self.radar_size / 1024)
        y = ry + int(py * self.radar_size / 1024)
        
        color = Colors.CT_DARK if p['team'] == 'CT' else Colors.T_DARK
        
        # X mark
        pygame.draw.line(self.screen, color, (x - 6, y - 6), (x + 6, y + 6), 3)
        pygame.draw.line(self.screen, color, (x + 6, y - 6), (x - 6, y + 6), 3)
    
    def _render_kill_feed(self):
        kx = self.width - 280
        ky = 70
        
        for i, kill in enumerate(self.recent_kills[-5:]):
            y = ky + i * 28
            
            pygame.draw.rect(self.screen, (0, 0, 0, 180), (kx, y, 260, 24), border_radius=4)
            
            killer_color = Colors.CT_PRIMARY if kill['attacker_team'] == 'CT' else Colors.T_PRIMARY
            killer = self.font_small.render(kill['attacker_name'], True, killer_color)
            self.screen.blit(killer, (kx + 8, y + 5))
            
            weapon = self.font_small.render(f"[{kill['weapon']}]", True, Colors.TEXT_GRAY)
            self.screen.blit(weapon, (kx + 90, y + 5))
            
            hs = " ⬤" if kill['headshot'] else ""
            victim = self.font_small.render(kill['victim_name'] + hs, True, Colors.HEALTH_LOW)
            self.screen.blit(victim, (kx + 165, y + 5))
    
    def _render_timeline(self):
        ty = self.height - 55
        tx, tw, th = 350, self.width - 380, 25
        
        # Background
        pygame.draw.rect(self.screen, Colors.BG_PANEL, (tx - 15, ty - 8, tw + 30, th + 16), border_radius=8)
        pygame.draw.rect(self.screen, Colors.BG_CARD, (tx, ty, tw, th), border_radius=4)
        
        if self.all_ticks:
            progress = self.current_tick_idx / max(1, len(self.all_ticks) - 1)
            
            # Progress gradient
            prog_w = int(tw * progress)
            if prog_w > 0:
                pygame.draw.rect(self.screen, Colors.ACCENT_CYAN, (tx, ty, prog_w, th), border_radius=4)
            
            # Playhead
            head_x = tx + prog_w
            pygame.draw.circle(self.screen, Colors.TEXT_WHITE, (head_x, ty + th//2), 10)
            pygame.draw.circle(self.screen, Colors.ACCENT_CYAN, (head_x, ty + th//2), 6)
            
            # Round markers
            for start, end, rnum in self.rounds:
                if start in self.all_ticks:
                    idx = self.all_ticks.index(start)
                    mx = tx + int(idx / max(1, len(self.all_ticks) - 1) * tw)
                    pygame.draw.line(self.screen, Colors.TEXT_DARK, (mx, ty - 4), (mx, ty + 2), 2)
            
            # Time display
            tick = self.all_ticks[self.current_tick_idx]
            secs = tick // 64
            mins, secs = secs // 60, secs % 60
            time_str = f"{mins}:{secs:02d}"
            time_text = self.font_body.render(time_str, True, Colors.TEXT_WHITE)
            self.screen.blit(time_text, (tx - 60, ty + 3))
    
    def _render_controls_hint(self):
        cy = self.height - 20
        hints = "SPACE: Play  ←→: Seek  ↑↓: Speed  E/R: Round  HOME/END: Start/End"
        text = self.font_small.render(hints, True, Colors.TEXT_DARK)
        self.screen.blit(text, (20, cy))


def main():
    import argparse
    parser = argparse.ArgumentParser(description='SACRILEGE RADAR')
    parser.add_argument('demo', nargs='?', help='Demo file path')
    args = parser.parse_args()
    
    replayer = RadarReplayer(1400, 900)
    
    if args.demo:
        demo_path = Path(args.demo)
        if demo_path.exists():
            replayer.load_demo(demo_path)
    else:
        demo_dir = Path(__file__).parent.parent / 'demo files'
        if demo_dir.exists():
            demos = list(demo_dir.glob('*.dem'))
            if demos:
                replayer.load_demo(demos[0])
    
    replayer.run()


if __name__ == '__main__':
    main()

# Sacrilege Engine - Parsing Pipeline

## Overview

The parsing pipeline converts raw `.dem` files into structured, queryable data.

---

## Pipeline Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Upload    │────▶│  Validate   │────▶│    Parse    │────▶│  Extract    │
│   .dem      │     │   Header    │     │   Ticks     │     │   Events    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                   │
                                                                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Store     │◀────│  Compute    │◀────│ Reconstruct │◀────│   Track     │
│   to DB     │     │ Visibility  │     │   World     │     │  Players    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

---

## Stage 1: Demo Validation

```python
class DemoValidator:
    """Validates demo file before processing."""
    
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    SUPPORTED_VERSIONS = ["cs2_demo_14", "cs2_demo_15"]
    
    def validate(self, file_path: Path) -> ValidationResult:
        """
        Validation steps:
        1. Check file exists and is readable
        2. Verify file size within limits
        3. Check magic bytes (demo header signature)
        4. Parse header for version compatibility
        5. Verify file integrity (not truncated)
        """
        
        # File existence
        if not file_path.exists():
            return ValidationResult(valid=False, error="File not found")
        
        # Size check
        if file_path.stat().st_size > self.MAX_FILE_SIZE:
            return ValidationResult(valid=False, error="File too large")
        
        # Header validation
        with open(file_path, 'rb') as f:
            magic = f.read(8)
            if magic != b'PBDEMS2\x00':
                return ValidationResult(valid=False, error="Invalid demo format")
        
        # Version check via demoparser2
        try:
            header = self.parse_header(file_path)
            if header.version not in self.SUPPORTED_VERSIONS:
                return ValidationResult(
                    valid=False, 
                    error=f"Unsupported version: {header.version}"
                )
        except Exception as e:
            return ValidationResult(valid=False, error=f"Corrupt header: {e}")
        
        return ValidationResult(valid=True, header=header)
```

---

## Stage 2: Tick Parser

```python
from demoparser2 import DemoParser

class TickProcessor:
    """Processes demo tick-by-tick."""
    
    SAMPLE_RATE = 16  # Sample every 16 ticks (128 tick / 16 = 8 samples/sec)
    
    def __init__(self, demo_path: Path):
        self.parser = DemoParser(str(demo_path))
        self.tick_rate = None
        self.total_ticks = None
    
    def get_tick_data(self, fields: list[str]) -> pd.DataFrame:
        """
        Extract specific fields across all ticks.
        Uses demoparser2's optimized Rust backend.
        
        Fields available:
        - tick
        - steamid
        - name
        - team_num
        - X, Y, Z (position)
        - velocity_X, velocity_Y, velocity_Z
        - pitch, yaw (view angles)
        - health, armor
        - active_weapon
        - is_alive
        - money
        """
        return self.parser.parse_ticks(fields)
    
    def sample_player_states(self) -> Iterator[PlayerState]:
        """
        Yield sampled player states for storage.
        Full tick data is too large to store.
        """
        df = self.get_tick_data([
            "tick", "steamid", "name", "team_num",
            "X", "Y", "Z",
            "velocity_X", "velocity_Y", "velocity_Z",
            "pitch", "yaw",
            "health", "armor", "has_helmet", "has_defuser",
            "active_weapon", "money", "equipment_value"
        ])
        
        # Sample every N ticks
        sampled = df[df['tick'] % self.SAMPLE_RATE == 0]
        
        for _, row in sampled.iterrows():
            yield PlayerState(
                tick=row['tick'],
                steam_id=row['steamid'],
                position=Vector3(row['X'], row['Y'], row['Z']),
                velocity=Vector3(row['velocity_X'], row['velocity_Y'], row['velocity_Z']),
                view_angles=ViewAngles(row['pitch'], row['yaw']),
                health=row['health'],
                armor=row['armor'],
                # ... etc
            )
```

---

## Stage 3: Event Extractor

```python
class EventExtractor:
    """Extracts game events from demo."""
    
    EVENT_TYPES = {
        'weapon_fire': 'shot',
        'player_hurt': 'hit',
        'player_death': 'death',
        'flashbang_detonate': 'flash',
        'smokegrenade_detonate': 'smoke',
        'inferno_startburn': 'molotov',
        'hegrenade_detonate': 'he_grenade',
        'bomb_planted': 'bomb_plant',
        'bomb_defused': 'bomb_defuse',
        'bomb_exploded': 'bomb_explode',
        'round_start': 'round_start',
        'round_end': 'round_end',
    }
    
    def extract_events(self, parser: DemoParser) -> list[GameEvent]:
        """Extract all relevant events."""
        
        events = []
        
        # Get game events
        for event_name, internal_name in self.EVENT_TYPES.items():
            raw_events = parser.parse_event(event_name)
            
            for _, row in raw_events.iterrows():
                event = self.normalize_event(internal_name, row)
                events.append(event)
        
        # Sort by tick
        events.sort(key=lambda e: e.tick)
        
        return events
    
    def extract_shots(self, parser: DemoParser) -> list[ShotEvent]:
        """Extract weapon fire events with full context."""
        
        weapon_fire = parser.parse_event("weapon_fire", 
            extra_fields=["X", "Y", "Z", "pitch", "yaw", "weapon"])
        
        shots = []
        for _, row in weapon_fire.iterrows():
            shots.append(ShotEvent(
                tick=row['tick'],
                player_steamid=row['user_steamid'],
                position=Vector3(row['X'], row['Y'], row['Z']),
                view_angles=ViewAngles(row['pitch'], row['yaw']),
                weapon=row['weapon'],
            ))
        
        return shots
    
    def extract_kills(self, parser: DemoParser) -> list[KillEvent]:
        """Extract kills with attacker/victim context."""
        
        deaths = parser.parse_event("player_death",
            extra_fields=[
                "attacker_X", "attacker_Y", "attacker_Z",
                "user_X", "user_Y", "user_Z",
                "weapon", "headshot", "penetrated", "noscope"
            ])
        
        kills = []
        for _, row in deaths.iterrows():
            kills.append(KillEvent(
                tick=row['tick'],
                attacker_steamid=row['attacker_steamid'],
                victim_steamid=row['user_steamid'],
                attacker_position=Vector3(row['attacker_X'], row['attacker_Y'], row['attacker_Z']),
                victim_position=Vector3(row['user_X'], row['user_Y'], row['user_Z']),
                weapon=row['weapon'],
                headshot=row['headshot'],
                penetrated=row['penetrated'],
                noscope=row.get('noscope', False),
            ))
        
        return kills
    
    def extract_utility(self, parser: DemoParser) -> list[UtilityEvent]:
        """Extract all utility usage."""
        
        utility_events = []
        
        # Flashbangs
        flashes = parser.parse_event("flashbang_detonate",
            extra_fields=["X", "Y", "Z", "entityid"])
        for _, row in flashes.iterrows():
            utility_events.append(UtilityEvent(
                type='flash',
                tick=row['tick'],
                player_steamid=row['user_steamid'],
                position=Vector3(row['X'], row['Y'], row['Z']),
            ))
        
        # Add blind durations from player_blind events
        blinds = parser.parse_event("player_blind")
        # ... correlate with flash events
        
        # Smokes, mollies, HEs similarly...
        
        return utility_events
```

---

## Stage 4: Player Tracker

```python
class PlayerTracker:
    """Tracks player state throughout demo."""
    
    def __init__(self):
        self.players: dict[str, PlayerInfo] = {}
        self.positions: dict[str, list[TimestampedPosition]] = {}
    
    def track_players(self, parser: DemoParser, events: list[GameEvent]) -> dict[str, PlayerInfo]:
        """Build complete player tracking data."""
        
        # Get player info from header
        player_info = parser.parse_player_info()
        
        for _, row in player_info.iterrows():
            steam_id = row['steamid']
            self.players[steam_id] = PlayerInfo(
                steam_id=steam_id,
                name=row['name'],
                team=self.get_team(row['team_num']),
            )
        
        # Aggregate round-by-round stats
        for event in events:
            if event.type == 'kill':
                self.players[event.attacker_steamid].kills += 1
                self.players[event.victim_steamid].deaths += 1
            elif event.type == 'hit':
                self.players[event.attacker_steamid].damage_dealt += event.damage
        
        return self.players
    
    def get_player_position_at_tick(self, steam_id: str, tick: int) -> Vector3:
        """Get interpolated player position at specific tick."""
        
        positions = self.positions[steam_id]
        
        # Binary search for nearest samples
        before = self.find_nearest_before(positions, tick)
        after = self.find_nearest_after(positions, tick)
        
        if before is None:
            return after.position
        if after is None:
            return before.position
        
        # Linear interpolation
        t = (tick - before.tick) / (after.tick - before.tick)
        return Vector3.lerp(before.position, after.position, t)
```

---

## Stage 5: World Reconstruction

```python
class WorldReconstructor:
    """Reconstructs world state at any tick."""
    
    def __init__(self, map_geometry: MapGeometry):
        self.map_geometry = map_geometry
        self.visibility_cache = LRUCache(maxsize=10000)
    
    def get_world_state(self, tick: int, player_states: dict[str, PlayerState]) -> WorldState:
        """Build complete world state at specific tick."""
        
        state = WorldState(tick=tick)
        
        for steam_id, player_state in player_states.items():
            state.players[steam_id] = player_state
        
        # Compute visibility matrix
        state.visibility_matrix = self.compute_visibility(player_states)
        
        # Compute angle exposure
        state.angle_exposure = self.compute_angle_exposure(player_states)
        
        # Get active utility effects
        state.active_smokes = self.get_active_smokes(tick)
        state.active_mollies = self.get_active_mollies(tick)
        
        return state
    
    def compute_visibility(self, players: dict[str, PlayerState]) -> VisibilityMatrix:
        """Compute who can see whom."""
        
        matrix = VisibilityMatrix()
        
        alive_players = [p for p in players.values() if p.is_alive]
        
        for viewer in alive_players:
            for target in alive_players:
                if viewer.steam_id == target.steam_id:
                    continue
                if viewer.team == target.team:
                    continue
                
                can_see = self.check_line_of_sight(
                    viewer.position + EYE_OFFSET,
                    target.position + EYE_OFFSET,
                    viewer.view_angles,
                    viewer.is_flashed
                )
                
                matrix.set(viewer.steam_id, target.steam_id, can_see)
        
        return matrix
```

---

## Stage 6: Visibility System (LOS Raycasting)

```python
class VisibilitySystem:
    """Handles line-of-sight calculations."""
    
    FOV_HORIZONTAL = 90  # degrees
    FOV_VERTICAL = 74    # degrees
    MAX_VISIBILITY_DISTANCE = 3000  # units
    
    def __init__(self, map_geometry: MapGeometry):
        self.map = map_geometry
        self.bsp_tree = map_geometry.bsp_tree  # Precomputed BSP for fast raycasts
    
    def check_line_of_sight(
        self,
        viewer_pos: Vector3,
        target_pos: Vector3,
        viewer_angles: ViewAngles,
        is_flashed: bool
    ) -> VisibilityResult:
        """
        Determine if viewer can see target.
        
        Steps:
        1. Check if target is within FOV
        2. Check distance
        3. Raycast for obstructions
        4. Check smoke occlusion
        5. Account for flash blindness
        """
        
        if is_flashed:
            return VisibilityResult(visible=False, reason='flashed')
        
        # Direction to target
        direction = (target_pos - viewer_pos).normalized()
        distance = viewer_pos.distance_to(target_pos)
        
        if distance > self.MAX_VISIBILITY_DISTANCE:
            return VisibilityResult(visible=False, reason='distance')
        
        # FOV check
        forward = viewer_angles.to_forward_vector()
        angle_to_target = math.degrees(math.acos(forward.dot(direction)))
        
        if angle_to_target > self.FOV_HORIZONTAL / 2:
            return VisibilityResult(visible=False, reason='fov')
        
        # Raycast against map geometry
        hit = self.bsp_tree.raycast(viewer_pos, target_pos)
        if hit.did_hit and hit.distance < distance:
            return VisibilityResult(visible=False, reason='occluded', hit_point=hit.point)
        
        # Smoke check
        if self.is_blocked_by_smoke(viewer_pos, target_pos):
            return VisibilityResult(visible=False, reason='smoke')
        
        return VisibilityResult(
            visible=True,
            distance=distance,
            angle_offset=angle_to_target
        )
    
    def is_blocked_by_smoke(self, start: Vector3, end: Vector3) -> bool:
        """Check if line passes through active smoke."""
        
        for smoke in self.active_smokes:
            if smoke.intersects_line(start, end):
                return True
        return False
    
    def compute_angle_exposure(self, player: PlayerState, enemies: list[PlayerState]) -> AngleExposure:
        """
        Compute how many angles a player is exposed to.
        
        Returns number of enemies who have LOS on player,
        and their relative angles.
        """
        
        exposures = []
        
        for enemy in enemies:
            if not enemy.is_alive:
                continue
            
            los = self.check_line_of_sight(
                enemy.position + EYE_OFFSET,
                player.position + EYE_OFFSET,
                enemy.view_angles,
                enemy.is_flashed
            )
            
            if los.visible:
                rel_angle = self.compute_relative_angle(player, enemy)
                exposures.append(AngleExposureEntry(
                    enemy_id=enemy.steam_id,
                    angle=rel_angle,
                    distance=los.distance
                ))
        
        return AngleExposure(
            exposure_count=len(exposures),
            exposures=exposures,
            is_crossfire=self.is_crossfire(exposures)
        )
```

---

## Stage 7: Map Geometry Loader

```python
class MapGeometryLoader:
    """Loads and manages map geometry data."""
    
    MAPS_DIR = Path("config/maps")
    
    # Map dimensions (world units)
    MAP_DATA = {
        "de_dust2": {"origin": Vector3(-2476, 3239, -110), "scale": 4.4},
        "de_mirage": {"origin": Vector3(-3230, 1713, -110), "scale": 5.0},
        "de_inferno": {"origin": Vector3(-2087, 3870, -110), "scale": 4.9},
        "de_nuke": {"origin": Vector3(-3453, 2887, -742), "scale": 7.0},
        "de_overpass": {"origin": Vector3(-4831, 1781, 0), "scale": 5.2},
        "de_ancient": {"origin": Vector3(-2953, 2164, -110), "scale": 5.0},
        "de_anubis": {"origin": Vector3(-2796, 3328, -110), "scale": 5.22},
        "de_vertigo": {"origin": Vector3(-3168, 1762, -110), "scale": 4.0},
    }
    
    def load_map(self, map_name: str) -> MapGeometry:
        """Load map geometry from JSON files."""
        
        map_path = self.MAPS_DIR / f"{map_name}.json"
        
        if not map_path.exists():
            raise MapNotFoundError(f"Unknown map: {map_name}")
        
        with open(map_path) as f:
            data = json.load(f)
        
        return MapGeometry(
            name=map_name,
            clip_brushes=self.load_clip_brushes(data['clip_brushes']),
            nav_mesh=self.load_nav_mesh(data['nav_mesh']),
            callout_zones=self.load_callout_zones(data['callouts']),
            spawn_points=data['spawns'],
            bombsites=data['bombsites'],
            bsp_tree=self.build_bsp_tree(data['clip_brushes']),
            radar_origin=Vector3(*self.MAP_DATA[map_name]['origin']),
            radar_scale=self.MAP_DATA[map_name]['scale'],
        )
    
    def build_bsp_tree(self, brushes: list[dict]) -> BSPTree:
        """Build BSP tree for fast raycast queries."""
        
        polygons = []
        for brush in brushes:
            polygons.extend(self.brush_to_polygons(brush))
        
        return BSPTree.build(polygons)
    
    def world_to_radar(self, position: Vector3, map_name: str) -> tuple[float, float]:
        """Convert world coordinates to radar image coordinates."""
        
        origin = self.MAP_DATA[map_name]['origin']
        scale = self.MAP_DATA[map_name]['scale']
        
        radar_x = (position.x - origin.x) / scale
        radar_y = (origin.y - position.y) / scale  # Y is inverted
        
        return (radar_x, radar_y)
```

---

## Stage 8: Sound Event Extraction

```python
class SoundEventExtractor:
    """Extract and process sound cues."""
    
    SOUND_RADIUS = {
        'footstep': 1100,       # ~18m
        'weapon_fire': 2000,    # Varies by weapon
        'reload': 800,
        'scope': 600,
        'land': 1000,
        'fall_damage': 1500,
        'grenade_bounce': 800,
    }
    
    def extract_sound_cues(
        self,
        player_states: dict[int, dict[str, PlayerState]],
        events: list[GameEvent]
    ) -> list[SoundEvent]:
        """
        Infer sound events from player actions.
        
        Sound cues inform decision-making analysis.
        """
        
        sounds = []
        
        # Footstep detection from velocity
        for tick, states in player_states.items():
            for steam_id, state in states.items():
                if self.is_making_footstep_sound(state):
                    sounds.append(SoundEvent(
                        tick=tick,
                        type='footstep',
                        source_id=steam_id,
                        position=state.position,
                        radius=self.SOUND_RADIUS['footstep']
                    ))
        
        # Weapon fire sounds from shot events
        for event in events:
            if event.type == 'shot':
                sounds.append(SoundEvent(
                    tick=event.tick,
                    type='weapon_fire',
                    source_id=event.player_steamid,
                    position=event.position,
                    radius=self.get_weapon_sound_radius(event.weapon)
                ))
        
        return sounds
    
    def is_making_footstep_sound(self, state: PlayerState) -> bool:
        """Determine if player is making footstep sounds."""
        
        # Must be alive and moving above walk speed
        if not state.is_alive:
            return False
        
        speed = state.velocity.magnitude()
        is_ducking = state.flags & FL_DUCKING
        
        # Walk speed thresholds
        max_silent_speed = 134 if not is_ducking else 85
        
        return speed > max_silent_speed and state.on_ground
    
    def can_hear_sound(self, listener: PlayerState, sound: SoundEvent) -> bool:
        """Check if player can hear a sound event."""
        
        distance = listener.position.distance_to(sound.position)
        return distance <= sound.radius
```

---

## Pipeline Orchestrator

```python
class DemoPipeline:
    """Orchestrates full demo processing."""
    
    def __init__(self, db: Database, config: PipelineConfig):
        self.db = db
        self.config = config
        self.validator = DemoValidator()
        self.map_loader = MapGeometryLoader()
    
    async def process_demo(self, demo_path: Path, user_id: UUID) -> ProcessResult:
        """Full processing pipeline."""
        
        # Stage 1: Validate
        validation = self.validator.validate(demo_path)
        if not validation.valid:
            return ProcessResult(success=False, error=validation.error)
        
        # Create demo record
        demo = await self.db.create_demo(
            file_path=demo_path,
            file_hash=self.compute_hash(demo_path),
            user_id=user_id,
            header=validation.header
        )
        
        try:
            # Stage 2: Parse ticks
            parser = DemoParser(str(demo_path))
            tick_processor = TickProcessor(parser)
            
            # Stage 3: Extract events
            event_extractor = EventExtractor()
            events = event_extractor.extract_events(parser)
            
            # Stage 4: Track players
            player_tracker = PlayerTracker()
            players = player_tracker.track_players(parser, events)
            
            # Store base data
            await self.db.store_events(demo.id, events)
            await self.db.store_players(demo.id, players)
            
            # Stage 5: Load map geometry
            map_geometry = self.map_loader.load_map(validation.header.map_name)
            
            # Stage 6: Reconstruct world (per round)
            reconstructor = WorldReconstructor(map_geometry)
            
            for round_data in self.get_rounds(events):
                round_states = tick_processor.get_round_states(round_data)
                
                # Store sampled states
                await self.db.store_player_states(
                    demo.id,
                    round_data.id,
                    self.sample_states(round_states)
                )
                
                # Stage 7: Compute visibility at key moments
                for tick in round_data.key_ticks:
                    world_state = reconstructor.get_world_state(tick, round_states[tick])
                    await self.db.store_visibility_snapshot(round_data.id, tick, world_state)
            
            # Mark complete
            await self.db.update_demo_status(demo.id, 'complete')
            
            return ProcessResult(success=True, demo_id=demo.id)
            
        except Exception as e:
            await self.db.update_demo_status(demo.id, 'failed', error=str(e))
            raise
```

---

## Performance Optimizations

### 1. Streaming Processing
```python
# Process in chunks, don't load entire demo into memory
for chunk in parser.iter_ticks(chunk_size=10000):
    process_chunk(chunk)
```

### 2. Parallel Event Extraction
```python
# Extract different event types in parallel
async with asyncio.TaskGroup() as tg:
    shots_task = tg.create_task(extract_shots(parser))
    kills_task = tg.create_task(extract_kills(parser))
    utility_task = tg.create_task(extract_utility(parser))
```

### 3. Visibility Caching
```python
# Cache visibility results per tick
@lru_cache(maxsize=10000)
def get_cached_visibility(tick: int) -> VisibilityMatrix:
    return compute_visibility(tick)
```

### 4. BSP Tree for Raycasting
```python
# O(log n) raycasts instead of O(n)
bsp_tree = BSPTree.build(map_polygons)
hit = bsp_tree.raycast(start, end)  # Fast!
```

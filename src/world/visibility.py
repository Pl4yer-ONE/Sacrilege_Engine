"""Visibility and Line-of-Sight system."""

from dataclasses import dataclass, field
from typing import Optional
import math

from src.models import Vector3, PlayerState, Team
from src.world.map_geometry import MapLoader, MapGeometry


@dataclass
class VisibilityInfo:
    """Visibility information between two players."""
    observer_id: str
    target_id: str
    
    has_los: bool = False  # Clear line of sight
    distance: float = 0.0
    angle_offset: float = 0.0  # How far target is from crosshair
    
    blocked_by_smoke: bool = False
    target_flashed: bool = False
    
    # Additional context
    callout: str = ""


@dataclass
class SmokeCloud:
    """Active smoke grenade."""
    position: Vector3
    start_tick: int
    end_tick: int
    
    # Smoke radius (approximately 144 units in CS2)
    RADIUS = 144.0
    
    def is_active(self, tick: int) -> bool:
        """Check if smoke is active at tick."""
        return self.start_tick <= tick <= self.end_tick
    
    def blocks_los(self, pos1: Vector3, pos2: Vector3) -> bool:
        """Check if smoke blocks line of sight between two positions."""
        # Ray-sphere intersection
        return self._ray_intersects_sphere(pos1, pos2, self.position, self.RADIUS)
    
    def _ray_intersects_sphere(
        self, 
        ray_start: Vector3, 
        ray_end: Vector3, 
        sphere_center: Vector3, 
        radius: float
    ) -> bool:
        """Check if a line segment intersects a sphere."""
        # Ray direction
        dx = ray_end.x - ray_start.x
        dy = ray_end.y - ray_start.y
        dz = ray_end.z - ray_start.z
        
        # Vector from ray start to sphere center
        fx = ray_start.x - sphere_center.x
        fy = ray_start.y - sphere_center.y
        fz = ray_start.z - sphere_center.z
        
        # Quadratic coefficients
        a = dx * dx + dy * dy + dz * dz
        
        if a == 0:
            # Zero-length ray
            return sphere_center.distance_to(ray_start) <= radius
        
        b = 2 * (fx * dx + fy * dy + fz * dz)
        c = fx * fx + fy * fy + fz * fz - radius * radius
        
        discriminant = b * b - 4 * a * c
        
        if discriminant < 0:
            return False
        
        discriminant = math.sqrt(discriminant)
        t1 = (-b - discriminant) / (2 * a)
        t2 = (-b + discriminant) / (2 * a)
        
        # Check if intersection is between start (t=0) and end (t=1)
        # Also check if segment is entirely inside sphere (t1 < 0 and t2 > 1)
        if (0 <= t1 <= 1) or (0 <= t2 <= 1):
            return True
        
        # Check if segment is entirely inside the sphere
        if t1 < 0 and t2 > 1:
            return True
        
        return False


class VisibilitySystem:
    """
    Computes visibility between players.
    
    Features:
    - Line-of-sight checking
    - Smoke occlusion
    - Distance and angle calculation
    - Visibility matrix per tick
    
    Note: Full BSP-based raycasting would require map NAV files.
    This implementation uses simplified distance/angle checks plus smoke occlusion.
    """
    
    # Maximum visibility distance (units)
    MAX_VISIBILITY_DISTANCE = 4000.0
    
    # Field of view (degrees)
    FOV = 106.0  # CS2 default FOV
    
    def __init__(self, map_name: str = ""):
        self.map_geometry = MapLoader.get_map(map_name)
        self.active_smokes: list[SmokeCloud] = []
    
    def add_smoke(self, smoke: SmokeCloud) -> None:
        """Add a smoke cloud to track."""
        self.active_smokes.append(smoke)
    
    def clear_smokes(self) -> None:
        """Clear all tracked smokes."""
        self.active_smokes.clear()
    
    def compute_visibility(
        self,
        observer: PlayerState,
        target: PlayerState,
        tick: int
    ) -> VisibilityInfo:
        """
        Compute visibility from observer to target.
        
        Checks:
        1. Distance within range
        2. Target in FOV
        3. No smoke blocking
        4. Flash status
        """
        # Get positions (eye level)
        obs_pos = self._eye_position(observer.position)
        tgt_pos = self._eye_position(target.position)
        
        # Calculate distance
        distance = obs_pos.distance_to(tgt_pos)
        
        # Calculate angle to target
        to_target = tgt_pos - obs_pos
        angle_offset = observer.view_angles.angle_to(to_target)
        
        # Get callout for target position
        callout = ""
        if self.map_geometry:
            callout = self.map_geometry.get_callout_at(target.position)
        
        # Check basic visibility conditions
        if distance > self.MAX_VISIBILITY_DISTANCE:
            return VisibilityInfo(
                observer_id=observer.steam_id,
                target_id=target.steam_id,
                has_los=False,
                distance=distance,
                angle_offset=angle_offset,
                callout=callout,
            )
        
        # Check if in field of view (peripheral awareness)
        in_fov = angle_offset <= (self.FOV / 2)
        
        # Check smoke occlusion
        blocked_by_smoke = self._check_smoke_blocking(obs_pos, tgt_pos, tick)
        
        # Check if observer is flashed
        observer_flashed = observer.is_flashed and observer.flash_duration > 0.5
        
        # Determine LOS
        has_los = (
            in_fov and 
            not blocked_by_smoke and 
            not observer_flashed and
            target.is_alive and
            observer.is_alive
        )
        
        return VisibilityInfo(
            observer_id=observer.steam_id,
            target_id=target.steam_id,
            has_los=has_los,
            distance=distance,
            angle_offset=angle_offset,
            blocked_by_smoke=blocked_by_smoke,
            target_flashed=target.is_flashed,
            callout=callout,
        )
    
    def compute_visibility_matrix(
        self,
        players: dict[str, PlayerState],
        tick: int
    ) -> dict[str, dict[str, VisibilityInfo]]:
        """
        Compute visibility between all players.
        
        Returns: {observer_id: {target_id: VisibilityInfo}}
        """
        matrix: dict[str, dict[str, VisibilityInfo]] = {}
        
        player_list = list(players.values())
        
        for observer in player_list:
            if not observer.is_alive:
                continue
                
            matrix[observer.steam_id] = {}
            
            for target in player_list:
                # Skip self
                if target.steam_id == observer.steam_id:
                    continue
                
                # Skip same team (typically we care about enemy visibility)
                if target.team == observer.team:
                    continue
                
                if not target.is_alive:
                    continue
                
                vis = self.compute_visibility(observer, target, tick)
                matrix[observer.steam_id][target.steam_id] = vis
        
        return matrix
    
    def get_visible_enemies(
        self,
        player: PlayerState,
        all_players: dict[str, PlayerState],
        tick: int
    ) -> list[VisibilityInfo]:
        """Get list of enemies visible to player."""
        visible = []
        
        for pid, other in all_players.items():
            if pid == player.steam_id:
                continue
            if other.team == player.team:
                continue
            if not other.is_alive:
                continue
            
            vis = self.compute_visibility(player, other, tick)
            if vis.has_los:
                visible.append(vis)
        
        return visible
    
    def _eye_position(self, pos: Vector3) -> Vector3:
        """Get eye position (standing height = +64 units)."""
        return Vector3(pos.x, pos.y, pos.z + 64)
    
    def _check_smoke_blocking(
        self, 
        pos1: Vector3, 
        pos2: Vector3, 
        tick: int
    ) -> bool:
        """Check if any active smoke blocks the line of sight."""
        for smoke in self.active_smokes:
            if smoke.is_active(tick) and smoke.blocks_los(pos1, pos2):
                return True
        return False
    
    def can_see_enemy_at_tick(
        self,
        observer_id: str,
        players: dict[str, PlayerState],
        tick: int
    ) -> bool:
        """Quick check if player can see any enemy."""
        observer = players.get(observer_id)
        if not observer or not observer.is_alive:
            return False
        
        visible = self.get_visible_enemies(observer, players, tick)
        return len(visible) > 0


@dataclass 
class WorldState:
    """
    Complete world state at a specific tick.
    
    Contains:
    - All player states
    - Active smokes
    - Visibility matrix
    """
    tick: int
    players: dict[str, PlayerState] = field(default_factory=dict)
    smokes: list[SmokeCloud] = field(default_factory=list)
    visibility_matrix: dict[str, dict[str, VisibilityInfo]] = field(default_factory=dict)


class WorldReconstructor:
    """
    Reconstructs game world state from parsed demo data.
    
    Provides:
    - Per-tick world snapshots
    - Visibility computation
    - Spatial queries
    """
    
    def __init__(self, map_name: str = ""):
        self.map_name = map_name
        self.visibility_system = VisibilitySystem(map_name)
        self.world_states: dict[int, WorldState] = {}
    
    def build_world_state(
        self,
        tick: int,
        players: dict[str, PlayerState],
        smokes: list[SmokeCloud]
    ) -> WorldState:
        """Build complete world state for a tick."""
        # Update visibility system with current smokes
        self.visibility_system.clear_smokes()
        for smoke in smokes:
            if smoke.is_active(tick):
                self.visibility_system.add_smoke(smoke)
        
        # Compute visibility matrix
        vis_matrix = self.visibility_system.compute_visibility_matrix(players, tick)
        
        world_state = WorldState(
            tick=tick,
            players=players,
            smokes=[s for s in smokes if s.is_active(tick)],
            visibility_matrix=vis_matrix,
        )
        
        self.world_states[tick] = world_state
        return world_state
    
    def get_state_at_tick(self, tick: int) -> Optional[WorldState]:
        """Get cached world state at tick."""
        return self.world_states.get(tick)
    
    def can_player_see_enemy(
        self,
        player_id: str,
        tick: int
    ) -> bool:
        """Check if player can see any enemy at tick."""
        state = self.world_states.get(tick)
        if not state:
            return False
        
        vis_entries = state.visibility_matrix.get(player_id, {})
        return any(v.has_los for v in vis_entries.values())

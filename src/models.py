"""Core data models for Sacrilege Engine."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import math


class Team(Enum):
    """Team enumeration."""
    CT = "ct"
    T = "t"
    SPEC = "spectator"


class PeekClassification(Enum):
    """Peek type classification."""
    SMART = "smart"
    INFO_BASED = "info"
    FORCED = "forced"
    EGO = "ego"
    PANIC = "panic"
    NEUTRAL = "neutral"


class TradeClassification(Enum):
    """Trade outcome classification."""
    PERFECT = "perfect"
    LATE = "late"
    MISSED = "missed"
    IMPOSSIBLE = "impossible"


class EventType(Enum):
    """Game event types."""
    SHOT = "shot"
    HIT = "hit"
    KILL = "kill"
    DEATH = "death"
    FLASH = "flash"
    SMOKE = "smoke"
    MOLOTOV = "molotov"
    HE_GRENADE = "he_grenade"
    BOMB_PLANT = "bomb_plant"
    BOMB_DEFUSE = "bomb_defuse"
    BOMB_EXPLODE = "bomb_explode"
    ROUND_START = "round_start"
    ROUND_END = "round_end"


@dataclass
class Vector3:
    """3D vector for positions and velocities."""
    x: float
    y: float
    z: float
    
    def distance_to(self, other: "Vector3") -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt(self.distance_squared_to(other))

    def distance_squared_to(self, other: "Vector3") -> float:
        """Calculate squared Euclidean distance to another point."""
        return (
            (self.x - other.x) ** 2
            + (self.y - other.y) ** 2
            + (self.z - other.z) ** 2
        )
    
    def distance_2d(self, other: "Vector3") -> float:
        """Calculate 2D distance (ignoring Z)."""
        return math.sqrt(self.distance_2d_squared(other))

    def distance_2d_squared(self, other: "Vector3") -> float:
        """Calculate squared 2D distance (ignoring Z)."""
        return (self.x - other.x) ** 2 + (self.y - other.y) ** 2
    
    def magnitude(self) -> float:
        """Calculate vector magnitude."""
        return math.sqrt(self.magnitude_squared())

    def magnitude_squared(self) -> float:
        """Calculate squared vector magnitude."""
        return self.x ** 2 + self.y ** 2 + self.z ** 2
    
    def normalized(self) -> "Vector3":
        """Return normalized vector."""
        mag = self.magnitude()
        if mag == 0:
            return Vector3(0, 0, 0)
        return Vector3(self.x / mag, self.y / mag, self.z / mag)
    
    def dot(self, other: "Vector3") -> float:
        """Dot product with another vector."""
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def __add__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> "Vector3":
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)
    
    @staticmethod
    def lerp(a: "Vector3", b: "Vector3", t: float) -> "Vector3":
        """Linear interpolation between two vectors."""
        return Vector3(
            a.x + (b.x - a.x) * t,
            a.y + (b.y - a.y) * t,
            a.z + (b.z - a.z) * t
        )


@dataclass
class ViewAngles:
    """Player view angles."""
    pitch: float  # Up/down (-89 to 89)
    yaw: float    # Left/right (0 to 360)
    
    def to_forward_vector(self) -> Vector3:
        """Convert view angles to forward direction vector."""
        pitch_rad = math.radians(self.pitch)
        yaw_rad = math.radians(self.yaw)
        
        return Vector3(
            math.cos(pitch_rad) * math.cos(yaw_rad),
            math.cos(pitch_rad) * math.sin(yaw_rad),
            -math.sin(pitch_rad)
        )
    
    def angle_to(self, direction: Vector3) -> float:
        """Calculate angle between view and a direction."""
        forward = self.to_forward_vector()
        dot = max(-1.0, min(1.0, forward.dot(direction.normalized())))
        return math.degrees(math.acos(dot))


@dataclass
class PlayerState:
    """Player state at a specific tick."""
    tick: int
    steam_id: str
    name: str
    team: Team
    
    position: Vector3
    velocity: Vector3
    view_angles: ViewAngles
    
    health: int
    armor: int
    has_helmet: bool = False
    has_defuser: bool = False
    
    is_alive: bool = True
    is_flashed: bool = False
    flash_duration: float = 0.0
    
    active_weapon: str = ""
    money: int = 0
    equipment_value: int = 0
    
    # Computed visibility
    visible_enemies: list[str] = field(default_factory=list)


@dataclass
class GameEvent:
    """Base game event."""
    tick: int
    event_type: EventType
    player_id: Optional[str] = None
    position: Optional[Vector3] = None


@dataclass
class KillEvent(GameEvent):
    """Kill event with full context."""
    attacker_id: str = ""
    victim_id: str = ""
    attacker_position: Optional[Vector3] = None
    victim_position: Optional[Vector3] = None
    weapon: str = ""
    headshot: bool = False
    penetrated: bool = False
    noscope: bool = False
    through_smoke: bool = False
    
    def __post_init__(self):
        self.event_type = EventType.KILL


@dataclass
class ShotEvent(GameEvent):
    """Weapon fire event."""
    weapon: str = ""
    view_angles: Optional[ViewAngles] = None
    
    def __post_init__(self):
        self.event_type = EventType.SHOT


@dataclass
class UtilityEvent(GameEvent):
    """Utility throw/detonation event."""
    throw_position: Optional[Vector3] = None
    land_position: Optional[Vector3] = None
    thrower_id: str = ""
    thrower_team: Optional[Team] = None


@dataclass
class FlashEvent(UtilityEvent):
    """Flashbang event with blind info."""
    enemies_blinded: int = 0
    teammates_blinded: int = 0
    self_flash: bool = False
    avg_blind_duration: float = 0.0
    
    def __post_init__(self):
        self.event_type = EventType.FLASH


@dataclass
class SmokeEvent(UtilityEvent):
    """Smoke grenade event."""
    start_tick: int = 0
    end_tick: int = 0
    
    def __post_init__(self):
        self.event_type = EventType.SMOKE


@dataclass
class RoundData:
    """Data for a single round."""
    round_number: int
    start_tick: int
    end_tick: int
    freeze_end_tick: int = 0
    
    winner: Optional[Team] = None
    win_reason: str = ""
    
    ct_equipment: int = 0
    t_equipment: int = 0
    ct_money: int = 0
    t_money: int = 0
    
    events: list[GameEvent] = field(default_factory=list)
    kills: list[KillEvent] = field(default_factory=list)


@dataclass
class PlayerInfo:
    """Player aggregate info for a demo."""
    steam_id: str
    name: str
    team: Team
    
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    damage: int = 0
    headshot_kills: int = 0
    
    @property
    def headshot_pct(self) -> float:
        if self.kills == 0:
            return 0.0
        return (self.headshot_kills / self.kills) * 100


@dataclass
class DemoHeader:
    """Demo file header information."""
    map_name: str
    tick_rate: float
    duration_ticks: int
    duration_seconds: float
    game_version: str = ""
    server_name: str = ""


@dataclass
class DemoData:
    """Complete parsed demo data."""
    header: DemoHeader
    players: dict[str, PlayerInfo]
    rounds: list[RoundData]
    events: list[GameEvent]

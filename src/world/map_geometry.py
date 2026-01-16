"""Map geometry data and loading."""

from dataclasses import dataclass, field
from typing import Optional
import json
from pathlib import Path

from src.models import Vector3


@dataclass
class MapBounds:
    """Map coordinate bounds."""
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float = -500
    max_z: float = 500


@dataclass
class CalloutZone:
    """A named area on the map."""
    name: str
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float = -1000
    max_z: float = 1000
    
    def contains(self, pos: Vector3) -> bool:
        """Check if position is within this zone."""
        return (
            self.min_x <= pos.x <= self.max_x and
            self.min_y <= pos.y <= self.max_y and
            self.min_z <= pos.z <= self.max_z
        )


@dataclass
class MapGeometry:
    """Map geometry and metadata."""
    name: str
    display_name: str
    
    # Radar/overview image settings
    radar_origin: Vector3
    radar_scale: float
    
    # Map bounds
    bounds: MapBounds
    
    # Named zones for callouts
    callout_zones: list[CalloutZone] = field(default_factory=list)
    
    # Bombsite locations
    bombsite_a: Optional[Vector3] = None
    bombsite_b: Optional[Vector3] = None
    
    def world_to_radar(self, pos: Vector3) -> tuple[float, float]:
        """Convert world coordinates to radar image coordinates."""
        radar_x = (pos.x - self.radar_origin.x) / self.radar_scale
        radar_y = (self.radar_origin.y - pos.y) / self.radar_scale  # Y inverted
        return (radar_x, radar_y)
    
    def get_callout_at(self, pos: Vector3) -> str:
        """Get callout name for a position."""
        for zone in self.callout_zones:
            if zone.contains(pos):
                return zone.name
        return "unknown"


# Pre-defined map data (CS2 coordinates)
MAP_DATA = {
    "de_dust2": MapGeometry(
        name="de_dust2",
        display_name="Dust II",
        radar_origin=Vector3(-2476, 3239, 0),
        radar_scale=4.4,
        bounds=MapBounds(-2476, 2108, -1250, 3239),
        bombsite_a=Vector3(1210, 2440, 100),
        bombsite_b=Vector3(-1352, 2523, 40),
        callout_zones=[
            CalloutZone("A Site", 800, 1700, 2100, 2900),
            CalloutZone("A Long", 1100, 2200, 800, 2100),
            CalloutZone("A Short", 300, 900, 1800, 2800),
            CalloutZone("B Site", -1900, -900, 2200, 2900),
            CalloutZone("B Tunnels", -2400, -1400, 800, 2200),
            CalloutZone("Mid", -600, 400, 300, 1600),
            CalloutZone("CT Spawn", -300, 700, 2600, 3300),
            CalloutZone("T Spawn", -900, 100, -1200, -500),
        ]
    ),
    "de_mirage": MapGeometry(
        name="de_mirage",
        display_name="Mirage",
        radar_origin=Vector3(-3230, 1713, 0),
        radar_scale=5.0,
        bounds=MapBounds(-3230, 1800, -3400, 1713),
        bombsite_a=Vector3(-286, -1897, -160),
        bombsite_b=Vector3(-2153, 765, -160),
        callout_zones=[
            CalloutZone("A Site", -700, 200, -2400, -1500),
            CalloutZone("A Ramp", -300, 500, -1500, -600),
            CalloutZone("A Palace", -1100, -400, -2700, -2100),
            CalloutZone("B Site", -2600, -1800, 400, 1200),
            CalloutZone("B Apps", -2300, -1500, -600, 400),
            CalloutZone("Mid", -800, 200, -600, 600),
            CalloutZone("Window", -600, 100, 400, 900),
            CalloutZone("CT Spawn", 500, 1400, -700, 200),
            CalloutZone("T Spawn", -1600, -800, -3500, -2800),
        ]
    ),
    "de_inferno": MapGeometry(
        name="de_inferno",
        display_name="Inferno",
        radar_origin=Vector3(-2087, 3870, 0),
        radar_scale=4.9,
        bounds=MapBounds(-2087, 2500, -800, 3870),
        bombsite_a=Vector3(2050, 500, 165),
        bombsite_b=Vector3(290, 2880, 165),
        callout_zones=[
            CalloutZone("A Site", 1600, 2500, 0, 900),
            CalloutZone("Apartments", 1800, 2600, 1000, 2200),
            CalloutZone("Pit", 1400, 2000, -400, 200),
            CalloutZone("B Site", -200, 700, 2400, 3400),
            CalloutZone("Banana", 300, 1200, 1500, 2600),
            CalloutZone("Mid", 200, 1200, 300, 1300),
            CalloutZone("CT Spawn", -1800, -800, 600, 1600),
            CalloutZone("T Spawn", 400, 1400, -700, 100),
        ]
    ),
    "de_ancient": MapGeometry(
        name="de_ancient",
        display_name="Ancient",
        radar_origin=Vector3(-2953, 2164, 0),
        radar_scale=5.0,
        bounds=MapBounds(-2953, 1500, -2400, 2164),
        bombsite_a=Vector3(-518, -1523, 20),
        bombsite_b=Vector3(-1700, 500, -20),
    ),
    "de_nuke": MapGeometry(
        name="de_nuke",
        display_name="Nuke",
        radar_origin=Vector3(-3453, 2887, 0),
        radar_scale=7.0,
        bounds=MapBounds(-3453, 2000, -3000, 2887),
        bombsite_a=Vector3(638, -1019, -414),
        bombsite_b=Vector3(479, -733, -742),
    ),
    "de_overpass": MapGeometry(
        name="de_overpass",
        display_name="Overpass",
        radar_origin=Vector3(-4831, 1781, 0),
        radar_scale=5.2,
        bounds=MapBounds(-4831, 1000, -3000, 1781),
    ),
    "de_anubis": MapGeometry(
        name="de_anubis",
        display_name="Anubis",
        radar_origin=Vector3(-2796, 3328, 0),
        radar_scale=5.22,
        bounds=MapBounds(-2796, 2000, -2500, 3328),
    ),
    "de_vertigo": MapGeometry(
        name="de_vertigo",
        display_name="Vertigo",
        radar_origin=Vector3(-3168, 1762, 0),
        radar_scale=4.0,
        bounds=MapBounds(-3168, 600, -2000, 1762),
    ),
    "de_train": MapGeometry(
        name="de_train",
        display_name="Train",
        radar_origin=Vector3(-2432, 2432, 0),
        radar_scale=4.7,
        bounds=MapBounds(-2432, 2000, -2000, 2432),
    ),
}


class MapLoader:
    """Loads and manages map geometry."""
    
    @staticmethod
    def get_map(map_name: str) -> Optional[MapGeometry]:
        """Get map geometry by name."""
        # Normalize name
        name = map_name.lower()
        if not name.startswith("de_"):
            name = f"de_{name}"
        
        return MAP_DATA.get(name)
    
    @staticmethod
    def get_available_maps() -> list[str]:
        """Get list of available maps."""
        return list(MAP_DATA.keys())
    
    @staticmethod
    def get_callout(map_name: str, position: Vector3) -> str:
        """Get callout for position on map."""
        map_geo = MapLoader.get_map(map_name)
        if not map_geo:
            return "unknown"
        return map_geo.get_callout_at(position)

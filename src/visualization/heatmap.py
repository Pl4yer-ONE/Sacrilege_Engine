"""Heatmap generation system."""

from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import json

from src.models import DemoData, Vector3, Team
from src.world.map_geometry import MapLoader, MapGeometry


@dataclass
class HeatmapPoint:
    """A single point on the heatmap."""
    x: float
    y: float
    z: float
    weight: float = 1.0
    round_number: int = 0
    tick: int = 0
    event_type: str = ""  # kill, death, flash, smoke


@dataclass
class HeatmapData:
    """Heatmap data for a player."""
    player_id: str
    player_name: str
    map_name: str
    
    # Point collections
    kill_positions: list[HeatmapPoint] = field(default_factory=list)
    death_positions: list[HeatmapPoint] = field(default_factory=list)
    flash_positions: list[HeatmapPoint] = field(default_factory=list)
    smoke_positions: list[HeatmapPoint] = field(default_factory=list)
    
    # Map bounds for normalization
    map_bounds: Optional[tuple[float, float, float, float]] = None  # min_x, max_x, min_y, max_y


class HeatmapGenerator:
    """
    Generates position heatmaps from demo data.
    
    Produces:
    - Kill positions
    - Death positions
    - Utility usage positions
    
    Output formats:
    - JSON for web visualization
    - SVG for static display
    """
    
    def __init__(self):
        pass
    
    def generate(self, demo_data: DemoData, player_id: str) -> HeatmapData:
        """Generate heatmap data for a player."""
        player_info = demo_data.players.get(player_id)
        if not player_info:
            return HeatmapData(player_id, "Unknown", demo_data.header.map_name)
        
        map_geo = MapLoader.get_map(demo_data.header.map_name)
        
        heatmap = HeatmapData(
            player_id=player_id,
            player_name=player_info.name,
            map_name=demo_data.header.map_name,
        )
        
        if map_geo:
            heatmap.map_bounds = (
                map_geo.bounds.min_x,
                map_geo.bounds.max_x,
                map_geo.bounds.min_y,
                map_geo.bounds.max_y,
            )
        
        # Extract positions from rounds
        for round_data in demo_data.rounds:
            for kill in round_data.kills:
                # Kill positions (where player got kills)
                if kill.attacker_id == player_id and kill.attacker_position:
                    heatmap.kill_positions.append(HeatmapPoint(
                        x=kill.attacker_position.x,
                        y=kill.attacker_position.y,
                        z=kill.attacker_position.z,
                        weight=2.0 if kill.headshot else 1.0,
                        round_number=round_data.round_number,
                        tick=kill.tick,
                        event_type="kill",
                    ))
                
                # Death positions (where player died)
                if kill.victim_id == player_id and kill.victim_position:
                    heatmap.death_positions.append(HeatmapPoint(
                        x=kill.victim_position.x,
                        y=kill.victim_position.y,
                        z=kill.victim_position.z,
                        weight=1.0,
                        round_number=round_data.round_number,
                        tick=kill.tick,
                        event_type="death",
                    ))
            
            # Flash positions
            for event in round_data.events:
                if hasattr(event, 'thrower_id') and event.thrower_id == player_id:
                    if hasattr(event, 'land_position') and event.land_position:
                        pos = event.land_position
                        event_type = "flash" if "flash" in str(type(event)).lower() else "smoke"
                        
                        if event_type == "flash":
                            heatmap.flash_positions.append(HeatmapPoint(
                                x=pos.x, y=pos.y, z=pos.z,
                                round_number=round_data.round_number,
                                tick=event.tick,
                                event_type=event_type,
                            ))
                        else:
                            heatmap.smoke_positions.append(HeatmapPoint(
                                x=pos.x, y=pos.y, z=pos.z,
                                round_number=round_data.round_number,
                                tick=event.tick,
                                event_type=event_type,
                            ))
        
        return heatmap
    
    def to_json(self, heatmap: HeatmapData) -> str:
        """Export heatmap as JSON for web visualization."""
        data = {
            "player_id": heatmap.player_id,
            "player_name": heatmap.player_name,
            "map_name": heatmap.map_name,
            "map_bounds": heatmap.map_bounds,
            "kills": [
                {"x": p.x, "y": p.y, "z": p.z, "weight": p.weight, "round": p.round_number}
                for p in heatmap.kill_positions
            ],
            "deaths": [
                {"x": p.x, "y": p.y, "z": p.z, "weight": p.weight, "round": p.round_number}
                for p in heatmap.death_positions
            ],
            "flashes": [
                {"x": p.x, "y": p.y, "z": p.z, "round": p.round_number}
                for p in heatmap.flash_positions
            ],
            "smokes": [
                {"x": p.x, "y": p.y, "z": p.z, "round": p.round_number}
                for p in heatmap.smoke_positions
            ],
            "stats": {
                "total_kills": len(heatmap.kill_positions),
                "total_deaths": len(heatmap.death_positions),
                "total_flashes": len(heatmap.flash_positions),
                "total_smokes": len(heatmap.smoke_positions),
            }
        }
        return json.dumps(data, indent=2)
    
    def to_svg(self, heatmap: HeatmapData, width: int = 800, height: int = 800) -> str:
        """Generate SVG visualization of heatmap."""
        # Get map bounds
        if heatmap.map_bounds:
            min_x, max_x, min_y, max_y = heatmap.map_bounds
        else:
            # Calculate from data
            all_x = [p.x for p in heatmap.kill_positions + heatmap.death_positions]
            all_y = [p.y for p in heatmap.kill_positions + heatmap.death_positions]
            if not all_x:
                return "<svg></svg>"
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)
        
        # Scale function
        def scale_x(x):
            if max_x == min_x:
                return width / 2
            return (x - min_x) / (max_x - min_x) * (width - 40) + 20
        
        def scale_y(y):
            if max_y == min_y:
                return height / 2
            return height - ((y - min_y) / (max_y - min_y) * (height - 40) + 20)
        
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
            f'<rect width="{width}" height="{height}" fill="#1a1a2e"/>',
            f'<text x="{width/2}" y="30" text-anchor="middle" fill="white" font-size="20">{heatmap.player_name} - {heatmap.map_name}</text>',
        ]
        
        # Draw deaths (red)
        for p in heatmap.death_positions:
            x, y = scale_x(p.x), scale_y(p.y)
            svg_parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="rgba(255,0,0,0.6)" stroke="red"/>'
            )
        
        # Draw kills (green)
        for p in heatmap.kill_positions:
            x, y = scale_x(p.x), scale_y(p.y)
            r = 6 + p.weight * 2
            svg_parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="rgba(0,255,0,0.6)" stroke="lime"/>'
            )
        
        # Legend
        svg_parts.extend([
            f'<circle cx="30" cy="{height-60}" r="8" fill="rgba(0,255,0,0.6)" stroke="lime"/>',
            f'<text x="50" y="{height-55}" fill="white" font-size="14">Kills ({len(heatmap.kill_positions)})</text>',
            f'<circle cx="30" cy="{height-35}" r="8" fill="rgba(255,0,0,0.6)" stroke="red"/>',
            f'<text x="50" y="{height-30}" fill="white" font-size="14">Deaths ({len(heatmap.death_positions)})</text>',
        ])
        
        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)
    
    def generate_all_players(self, demo_data: DemoData) -> dict[str, HeatmapData]:
        """Generate heatmaps for all players."""
        heatmaps = {}
        for player_id in demo_data.players:
            heatmaps[player_id] = self.generate(demo_data, player_id)
        return heatmaps

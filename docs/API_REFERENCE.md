# API Reference

## Analysis Orchestrator

The main entry point for demo analysis.

```python
from src.analysis_orchestrator import AnalysisOrchestrator

orchestrator = AnalysisOrchestrator()
result = orchestrator.analyze(demo_path, player_name)
```

### Methods

#### `analyze(demo_path: Path | str, player_name: str) -> AnalysisResult`

Analyzes a demo file for a specific player.

**Parameters:**
- `demo_path`: Path to the .dem file
- `player_name`: Name of the player to analyze

**Returns:** `AnalysisResult` with feedback and statistics

---

## Demo Parser

```python
from src.parser.demo_parser import DemoParser

parser = DemoParser()
result = parser.parse(demo_path)
```

### ParseResult

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | Whether parsing succeeded |
| `data` | DemoData | Parsed demo data |
| `error` | str | Error message if failed |

### DemoData

| Field | Type | Description |
|-------|------|-------------|
| `header` | DemoHeader | Map name, duration, etc. |
| `players` | dict[str, PlayerInfo] | Player information by steam ID |
| `rounds` | list[Round] | Round data with kills, events |

---

## Radar Replayer

```python
from radar.radar_replayer import RadarReplayer

replayer = RadarReplayer(width=1400, height=900)
replayer.load_demo(Path("demo.dem"))
replayer.run()  # Opens interactive window
```

### MapConfig

```python
from radar.radar_replayer import MAP_CONFIGS

mirage = MAP_CONFIGS['de_mirage']
px, py = mirage.world_to_radar(world_x, world_y, 1024)
```

---

## Visualization

### Heatmap Generator

```python
from src.visualization.heatmap import HeatmapGenerator

gen = HeatmapGenerator(demo_data)
kills = gen.generate('kills', player_id='76561198...')
deaths = gen.generate('deaths', player_id='76561198...')
```

### Timeline Generator

```python
from src.visualization.timeline import TimelineGenerator

gen = TimelineGenerator(demo_data)
timeline = gen.generate()
```

---

## Intelligence Modules

All modules inherit from `IntelligenceModule`:

```python
class IntelligenceModule(ABC):
    @abstractmethod
    def analyze(self, demo_data, player_id) -> list[Feedback]:
        pass
```

### Available Modules

| Module | Import |
|--------|--------|
| Peek IQ | `from src.intelligence.peek_iq import PeekIQModule` |
| Trade Discipline | `from src.intelligence.trade_discipline import TradeDisciplineModule` |
| Utility Intelligence | `from src.intelligence.utility_intelligence import UtilityIntelligenceModule` |
| Crosshair Discipline | `from src.intelligence.crosshair_discipline import CrosshairDisciplineModule` |
| Rotation IQ | `from src.intelligence.rotation_iq import RotationIQModule` |
| Tilt Detector | `from src.intelligence.tilt_detector import TiltDetectorModule` |
| Cheat Patterns | `from src.intelligence.cheat_patterns import CheatPatternModule` |
| Round Simulator | `from src.intelligence.round_simulator import RoundSimulatorModule` |

---

## Models

### Feedback

```python
@dataclass
class Feedback:
    category: FeedbackCategory
    severity: FeedbackSeverity
    message: str
    context: FeedbackContext
    timestamp: float
```

### Vector3

```python
@dataclass
class Vector3:
    x: float
    y: float
    z: float
```

### KillEvent

```python
@dataclass
class KillEvent:
    tick: int
    attacker_id: str
    victim_id: str
    attacker_position: Optional[Vector3]
    victim_position: Optional[Vector3]
    weapon: str
    headshot: bool
```

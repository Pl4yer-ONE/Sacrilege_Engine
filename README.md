<p align="center">
  <h1 align="center">⚡ Sacrilege Engine</h1>
  <p align="center">
    <strong>CS2 Demo Decision Intelligence System</strong>
  </p>
  <p align="center">
    <em>Stop watching your demos. Let AI tell you exactly what to fix.</em>
  </p>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#intelligence-modules">Modules</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#api">API</a>
</p>

---

## What is Sacrilege Engine?

Sacrilege Engine analyzes CS2 demo files and identifies your **decision-making mistakes** — not just your stats. It uses 8 intelligence modules to generate actionable feedback in the format:

```
TOP 3 MISTAKES:
1. Costly deaths: 2 high-impact rounds
2. Missed trades: 122 opportunities  
3. Tilt detected at Round 6

YOUR FIXES:
🎯 MECHANICAL: Practice crosshair at head height
🧠 TACTICAL: Position closer to teammates
💭 MENTAL: Don't change playstyle when losing
```

## Features

- **8 Intelligence Modules** — Analyzes peeks, trades, utility, rotations, crosshair placement, tilt, and more
- **Win Probability Simulator** — See how your deaths impacted round outcomes
- **Visibility System** — Line-of-sight with smoke occlusion for 9 CS2 maps
- **Fast Parsing** — Process demos in seconds using demoparser2
- **REST API** — Upload demos and retrieve analysis via HTTP
- **Top 3 + 3 Format** — Prioritized mistakes and categorized fixes

## Quick Start

### Prerequisites

- Python 3.9+
- CS2 demo files (.dem)

### Installation

```bash
git clone https://github.com/yourusername/sacrilege-engine.git
cd sacrilege-engine

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install demoparser2 pydantic pydantic-settings pandas numpy fastapi uvicorn python-multipart
```

### Analyze a Demo

```python
from pathlib import Path
from src.analysis_orchestrator import AnalysisOrchestrator
from src.output.feedback_generator import FeedbackGenerator

# Analyze
orchestrator = AnalysisOrchestrator()
result = orchestrator.analyze(Path("your_demo.dem"))

# Print report
fg = FeedbackGenerator()
for player_id, report in result.player_reports.items():
    print(fg.format_report_text(report))
```

### Start API Server

```bash
source venv/bin/activate
PYTHONPATH=. python3 -m src.cli server --port 8000
```

Then upload demos:
```bash
curl -X POST -F "file=@your_demo.dem" http://localhost:8000/v1/demos/upload
```

## Intelligence Modules

| Module | Score Range | What It Measures |
|--------|-------------|------------------|
| **Peek IQ** | 0-100 | Classifies peeks as smart, info-based, forced, ego, or panic |
| **Trade Discipline** | 0-100 | Detects perfect, late, missed, and impossible trades |
| **Crosshair Discipline** | 0-100 | Head-level tracking, pre-aim accuracy, flick dependency |
| **Utility Intelligence** | 0-100 | Flash effectiveness, self-flashes, team flashes |
| **Rotation IQ** | 0-100 | Over-rotation detection, info processing |
| **Tilt Detector** | 0-100 | Mental degradation, solo pushes, early deaths |
| **Cheat Patterns** | 0-100 | Suspicious statistical anomalies (not accusations) |
| **Round Simulator** | 0-100 | Win probability impact of deaths |

## Visibility System

The engine includes a complete visibility/LOS system:

- **9 CS2 Maps** — dust2, mirage, inferno, ancient, nuke, overpass, anubis, vertigo, train
- **Callout Zones** — Automatic position-to-callout mapping (A Site, B Apps, etc.)
- **Smoke Occlusion** — Ray-sphere intersection for smoke blocking
- **FOV Calculation** — 106° field of view checking

```python
from src.world.visibility import VisibilitySystem
from src.world.map_geometry import MapLoader

# Get callout for a position
mirage = MapLoader.get_map("de_mirage")
callout = mirage.get_callout_at(Vector3(-300, -2000, -160))  # "A Site"

# Check visibility between players
vis = VisibilitySystem("de_mirage")
result = vis.compute_visibility(player1, player2, tick)
print(f"Has LOS: {result.has_los}, Blocked by smoke: {result.blocked_by_smoke}")
```

## Architecture

```
src/
├── parser/           # Demo parsing pipeline
│   ├── validator.py      # File validation, magic bytes
│   ├── event_extractor.py # Kill/flash/smoke extraction
│   ├── player_tracker.py  # Player state tracking
│   └── demo_parser.py     # Main orchestrator
│
├── intelligence/     # 8 analysis modules
│   ├── peek_iq.py
│   ├── trade_discipline.py
│   ├── crosshair_discipline.py
│   ├── utility_intelligence.py
│   ├── rotation_iq.py
│   ├── tilt_detector.py
│   ├── cheat_patterns.py
│   └── round_simulator.py
│
├── world/            # Visibility system
│   ├── map_geometry.py    # 9 map definitions
│   └── visibility.py      # LOS, smoke occlusion
│
├── output/           # Report generation
│   └── feedback_generator.py
│
├── api/              # REST API
│   └── main.py
│
└── analysis_orchestrator.py  # Main entry point
```

## API Reference

### Upload Demo
```http
POST /v1/demos/upload
Content-Type: multipart/form-data

file: <demo.dem>
```

### Check Status
```http
GET /v1/demos/{demo_id}/status
```

### Get Report
```http
GET /v1/demos/{demo_id}/report?player_id={steam_id}
```

### List Players
```http
GET /v1/demos/{demo_id}/players
```

## Configuration

Set environment variables or create `.env`:

```bash
SACRILEGE_DATABASE_URL=postgresql://localhost/sacrilege
SACRILEGE_REDIS_URL=redis://localhost:6379
SACRILEGE_MAX_DEMO_SIZE_MB=500
SACRILEGE_PLAYER_SAMPLE_RATE=32
```

## Documentation

See `/docs` for detailed documentation:

- [Architecture](docs/ARCHITECTURE.md) — System design and tech stack
- [Database Schema](docs/DATABASE_SCHEMA.md) — PostgreSQL tables
- [Parsing Pipeline](docs/PARSING_PIPELINE.md) — Demo processing stages
- [Intelligence Modules](docs/INTELLIGENCE_MODULES.md) — Module algorithms
- [API Reference](docs/API_REFERENCE.md) — Endpoint details
- [MVP Roadmap](docs/MVP_ROADMAP.md) — Development plan

## Tech Stack

- **Python 3.9+** — Core language
- **demoparser2** — CS2 demo parsing (Rust-based, fast)
- **FastAPI** — REST API framework
- **Pydantic** — Data validation
- **Pandas/NumPy** — Data processing

## License

MIT License — See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Built for players who want to improve, not just spectate.</strong>
</p>

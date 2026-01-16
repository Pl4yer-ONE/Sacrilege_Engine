# SACRILEGE ENGINE

## CS2 Demo Decision Intelligence System

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)

> **Analyze decisions, not stats.** A comprehensive Counter-Strike 2 demo analysis engine with AI-powered tactical intelligence and real-time radar replay visualization.

https://github.com/user-attachments/assets/radar_demo.mp4

**[▶ Watch Radar Demo Video](docs/radar_demo.mp4)** | [Download MP4](docs/radar_demo.mp4?raw=true)

---

## Features

### 🔬 Intelligence Modules
| Module | Description |
|--------|-------------|
| **Peek IQ** | Detects advantageous vs disadvantageous peek patterns |
| **Utility Intelligence** | Flash/smoke effectiveness and ROI analysis |
| **Trade Discipline** | Trade timing and positioning evaluation |
| **Crosshair Discipline** | Pre-aim and crosshair placement scoring |
| **Rotation IQ** | Rotation decision quality and timing |
| **Tilt Detector** | Mental state degradation detection |
| **Cheat Patterns** | Statistical anomaly detection |
| **Round Simulator** | Win probability modeling |

### 🎯 Radar Replayer
- **Native Python** visualization with pygame
- **Real map overlays** for all competitive maps
- **Tick-accurate** player positions and view angles
- **Utility visualization** (smokes, molotovs)
- **Timeline** with round navigation

### 📊 Visualization
- Heatmap generation (kills, deaths, utility)
- Timeline event sequences
- Decision graph visualization
- Team synergy analysis

---

## Quick Start

```bash
# Clone
git clone https://github.com/Pl4yer-ONE/Sacrilege_Engine.git
cd Sacrilege_Engine

# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .

# Analyze a demo
python -c "
from src.analysis_orchestrator import AnalysisOrchestrator
orchestrator = AnalysisOrchestrator()
result = orchestrator.analyze('your_demo.dem', 'PlayerName')
print(result.format_report())
"

# Run radar replayer
python radar/radar_replayer.py "path/to/demo.dem"
```

---

## Radar Controls

| Key | Action |
|-----|--------|
| `SPACE` | Play/Pause |
| `← →` | Seek backward/forward |
| `↑ ↓` | Speed up/slow down |
| `E / R` | Previous/Next round |
| `HOME / END` | Jump to start/end |

---

## Project Structure

```
Sacrilege_Engine/
├── src/
│   ├── parser/          # Demo parsing (demoparser2)
│   ├── intelligence/    # AI analysis modules
│   ├── visualization/   # Data visualization
│   └── world/           # Map geometry & visibility
├── radar/
│   ├── radar_replayer.py  # Native radar viewer
│   └── maps/              # Map overlay images
├── docs/                # Documentation
└── demo files/          # Sample demos
```

---

## Documentation

See [docs/TECHNICAL_PAPER.md](docs/TECHNICAL_PAPER.md) for detailed IEEE-format technical documentation.

---

## License

**Proprietary Commercial License** - See [LICENSE](LICENSE)

© 2026 Pl4yer-ONE. All rights reserved.

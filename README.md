# SACRILEGE ENGINE

<div align="center">

## CS2 Demo Decision Intelligence System

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey?style=for-the-badge)](/)

**Analyze decisions, not stats.**

A comprehensive Counter-Strike 2 demo analysis engine with AI-powered tactical intelligence and real-time radar replay visualization.

[![Radar Demo](docs/radar_preview.gif)](docs/radar_demo.mp4)

*↑ Click to watch full video ↑*

</div>

---

## ✨ Features

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
- **Real map overlays** for all 8 competitive maps
- **Tick-accurate** player positions
- **Live statistics** - HP, equipment, kills
- **Utility visualization** - smokes, molotovs, flashes, HEs

### 📊 Visualization
- Heatmap generation (kills, deaths, utility)
- Timeline event sequences
- Decision graph visualization

---

## 🚀 Quick Start

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

## 🎮 Radar Controls

| Key | Action |
|:---:|--------|
| `SPACE` | Play / Pause |
| `← →` | Seek backward / forward |
| `↑ ↓` | Speed up / down |
| `E` / `R` | Previous / Next round |
| `HOME` / `END` | Jump to start / end |

---

## 📁 Project Structure

```
Sacrilege_Engine/
├── src/
│   ├── parser/          # Demo parsing (demoparser2)
│   ├── intelligence/    # 8 AI analysis modules
│   ├── visualization/   # Heatmaps, timelines, graphs
│   └── world/           # Map geometry & visibility
├── radar/
│   ├── radar_replayer.py  # Native radar viewer
│   └── maps/              # Map overlay images
└── docs/                # Documentation
```

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Technical Paper](docs/TECHNICAL_PAPER.md) | IEEE-format system documentation |
| [API Reference](docs/API_REFERENCE.md) | Developer API guide |
| [Architecture](docs/ARCHITECTURE.md) | System design |
| [Intelligence Modules](docs/INTELLIGENCE_MODULES.md) | Module specifications |

---

## 🛠️ Requirements

- Python 3.9+
- pygame
- pandas
- demoparser2

---

## 📜 License

**Proprietary Commercial License** - See [LICENSE](LICENSE)

© 2026 Pl4yer-ONE. All rights reserved.

---

<div align="center">

**Built with ❤️ for the CS2 community**

</div>

<div align="center">

# SACRILEGE ENGINE

### *The Unforgiving CS2 Demo Intelligence System*

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![CS2](https://img.shields.io/badge/CS2-Demo%20Analysis-FF6B00?style=for-the-badge&logo=counter-strike)](https://counter-strike.net)
[![License](https://img.shields.io/badge/License-Proprietary-DC143C?style=for-the-badge)](LICENSE)

<br>

**Don't just watch demos. *Understand* them.**

Sacrilege Engine is a next-generation tactical intelligence platform that transforms raw CS2 demo files into actionable insights. Every death is dissected. Every mistake exposed. No mercy.

<br>

[![Radar Preview](docs/radar_preview.gif)](docs/radar_demo.mp4)

*Real-time death analysis with blame attribution and performance rankings*

---

[**Features**](#-features) · [**Quick Start**](#-quick-start) · [**Documentation**](#-documentation) · [**Philosophy**](#-philosophy)

</div>

---

## 🎯 Features

<table>
<tr>
<td width="50%">

### 💀 BRUTAL Death Analyzer
Every death gets dissected with **15 mistake classifications**:
- **ISOLATED** — Died alone, no support
- **CROSSFIRE** — Multiple angles exposed  
- **SOLO PUSH** — Rushed without team
- **NO TRADE** — Teammate didn't trade
- **FLASHED** — Killed while blind

Each death receives a **blame score (0-100%)** that feeds into live player rankings.

</td>
<td width="50%">

### 📊 Live Performance Rankings
Real-time **S/A/B/C/D/F grades** based on:
- Kill/Death ratio
- Average blame per death
- Tactical mistakes made
- Trade success rate

**Performance Score** = KD contribution - blame penalty

*No excuses. Just data.*

</td>
</tr>
<tr>
<td width="50%">

### 🗺️ Radar Replayer
Tick-perfect visualization with:
- All 8 competitive maps
- Player positions & health
- Utility tracking (smokes, mollies, flashes)
- Kill animations
- Death analysis popups

</td>
<td width="50%">

### 🧠 Intelligence Modules
8 specialized analysis engines:
- **Peek IQ** — Peek advantage detection
- **Trade Discipline** — Trade timing analysis
- **Utility ROI** — Flash/smoke effectiveness
- **Tilt Detector** — Mental state tracking
- **Cheat Patterns** — Statistical anomalies

</td>
</tr>
</table>

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

# Launch Radar Replayer
python radar/radar_replayer.py "path/to/demo.dem"
```

### Controls

| Key | Action |
|:---:|:-------|
| `SPACE` | Play / Pause |
| `← →` | Seek backward / forward |
| `↑ ↓` | Playback speed |
| `E` / `R` | Previous / Next round |

---

## 📖 Documentation

| Document | Description |
|:---------|:------------|
| [Technical Paper](docs/TECHNICAL_PAPER.md) | IEEE-format system documentation |
| [Architecture](docs/ARCHITECTURE.md) | System design & data flow |
| [Intelligence Modules](docs/INTELLIGENCE_MODULES.md) | Module specifications |
| [API Reference](docs/API_REFERENCE.md) | Developer integration guide |
| [Database Schema](docs/DATABASE_SCHEMA.md) | Data model reference |

---

## 🏗️ Project Structure

```
Sacrilege_Engine/
├── src/
│   ├── parser/              # Demo file parsing
│   ├── intelligence/        # Analysis modules
│   │   └── death_analyzer.py   # BRUTAL death analysis
│   ├── visualization/       # Heatmaps & graphs
│   └── world/              # Map geometry
├── radar/
│   ├── radar_replayer.py   # Main application
│   └── maps/               # Map overlays
└── docs/                   # Documentation
```

---

## 💡 Philosophy

> *"The truth hurts. Sacrilege delivers it anyway."*

Traditional demo review shows you *what* happened. Sacrilege tells you *why* — and assigns blame. Every isolated death, every missed trade, every stupid peek gets catalogued and scored.

**This isn't validation software. It's accountability software.**

Players who improve fastest are those who confront their mistakes honestly. Sacrilege makes that confrontation unavoidable.

---

## ⚙️ Requirements

- Python 3.9+
- pygame
- pandas
- demoparser2

---

## 📜 License

**Proprietary Commercial License**

© 2026 Pl4yer-ONE. All rights reserved. See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built for players who want the truth.**

*Not the comfortable version.*

<br>

[![GitHub](https://img.shields.io/badge/GitHub-Pl4yer--ONE-181717?style=flat-square&logo=github)](https://github.com/Pl4yer-ONE)

</div>

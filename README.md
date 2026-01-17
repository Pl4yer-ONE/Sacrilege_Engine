<div align="center">

<img src="docs/logo.png" alt="Sacrilege Engine Logo" width="200"/>

# SACRILEGE ENGINE

### *The Unforgiving CS2 Demo Intelligence System*

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![CS2](https://img.shields.io/badge/CS2-Demo%20Analysis-FF6B00?style=for-the-badge&logo=counter-strike)](https://counter-strike.net)
[![License](https://img.shields.io/badge/License-Proprietary-DC143C?style=for-the-badge)](LICENSE)

<br>

**Don't just watch demos. *Understand* them.**

Sacrilege Engine is a next-generation tactical intelligence platform that transforms raw CS2 demo files into actionable insights. Every death is dissected. Every mistake exposed. No mercy.

<br>

[![Radar Preview](docs/radar_preview.gif)](docs/radar_dust2.mp4)

*Real-time death analysis with blame attribution and performance rankings*

---

[**Demo Videos**](#-demo-videos) · [**Features**](#-features) · [**Quick Start**](#-quick-start) · [**Documentation**](#-documentation)

</div>

---

## 🎬 Demo Videos

| Map | Video | Description |
|:---:|:-----:|:------------|
| **Dust2** | [📹 Watch](docs/radar_dust2.mp4) | GamerLegion vs Venom - 10s tactical breakdown |
| **Mirage** | [📹 Watch](docs/radar_mirage.mp4) | EC Banga vs Semperfi - Live death analysis |

---

## 🎯 Features

<table>
<tr>
<td width="50%">

### 💀 BRUTAL Death Analyzer
Every death gets dissected with **15 mistake classifications**:

| Type | Severity | Description |
|:-----|:--------:|:------------|
| **ISOLATED** | 🔴 5 | Died alone, no support |
| **CROSSFIRE** | 🔴 5 | Multiple angles exposed |
| **SOLO PUSH** | 🔴 5 | Rushed without team |
| **NO TRADE** | 🟠 4 | Teammate didn't trade |
| **FLASHED** | 🟡 3 | Killed while blind |
| **FAIR DUEL** | ⚪ 1 | Lost aim battle |

Each death receives a **blame score (0-100%)**.

</td>
<td width="50%">

### 📊 Live Performance Rankings
Real-time **S/A/B/C/D/F grades** based on:

```
Grade = KD Ratio × 40 - Blame Penalty + 20
```

| Grade | Score | Meaning |
|:-----:|:-----:|:--------|
| **S** | 80+ | Elite performance |
| **A** | 65+ | Strong player |
| **B** | 50+ | Solid contribution |
| **C** | 35+ | Average play |
| **D** | 20+ | Underperforming |
| **F** | <20 | Liability |

</td>
</tr>
</table>

---

## 🔥 Death Analysis Popup

When a player dies, a detailed popup appears showing:

```
┌────────────────────────────────┐
│ PlayerName    killed by Enemy  │  ← Victim & Killer
│ CROSSFIRE                   [5]│  ← Primary Mistake + Severity
│                                │
│ Team: 892u    vs 3 enemies     │  ← Distance + Enemy count
│ NOT TRADED   Blame: 90%        │  ← Trade status + Blame
│ +ISOLATED, NO_TRADE            │  ← Additional mistakes
└────────────────────────────────┘
```

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
| [CHANGELOG](CHANGELOG.md) | Version history |
| [CONTRIBUTING](CONTRIBUTING.md) | Development guide |
| [Technical Paper](docs/TECHNICAL_PAPER.md) | IEEE-format documentation |

---

## 🏗️ Project Structure

```
Sacrilege_Engine/
├── src/
│   ├── parser/              # Demo file parsing
│   ├── intelligence/        # Analysis modules
│   │   └── death_analyzer.py   # BRUTAL death analysis
│   └── visualization/       # Heatmaps & graphs
├── radar/
│   ├── radar_replayer.py   # Main application
│   └── maps/               # Map overlays (8 maps)
└── docs/
    ├── radar_dust2.mp4     # Demo: Dust2
    ├── radar_mirage.mp4    # Demo: Mirage
    └── radar_preview.gif   # Preview animation
```

---

## 📊 Test Results

Rigorously tested across **4 maps, 330 deaths analyzed**:

| Map | Deaths | Top Mistakes |
|:----|:------:|:-------------|
| Dust2 | 81 | crossfire(44), isolated(31) |
| Ancient | 75 | crossfire(41), isolated(28) |
| Overpass | 89 | crossfire(55), isolated(25) |
| Mirage | 85 | crossfire(55), isolated(23) |

---

## 💡 Philosophy

> *"The truth hurts. Sacrilege delivers it anyway."*

Traditional demo review shows you *what* happened. Sacrilege tells you *why* — and assigns blame.

**This isn't validation software. It's accountability software.**

---

## ⚙️ Requirements

- Python 3.9+
- pygame
- pandas
- demoparser2

---

## 📜 License

**Proprietary Commercial License** — © 2026 Pl4yer-ONE

---

<div align="center">

**Built for players who want the truth.**

*Not the comfortable version.*

</div>

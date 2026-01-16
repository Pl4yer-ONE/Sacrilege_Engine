<div align="center">

# 🎯 SACRILEGE ENGINE

### CS2 Demo Decision Intelligence System

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Active-green.svg)]()

**Analyze decisions, not stats. Get better, not tilted.**

</div>

---

## What Is This?

Sacrilege Engine analyzes CS2 demo files to identify **decision-making mistakes** — not K/D ratios. It runs 8 intelligence modules to produce actionable feedback:

```
TOP 3 MISTAKES:
1. Costly deaths: 2 high-impact rounds [R8, R14]
2. Missed trades: 122 opportunities
3. Tilt detected at Round 6

YOUR FIXES:
🎯 MECHANICAL: Practice crosshair at head height
🧠 TACTICAL: Position closer to teammates
💭 MENTAL: Don't change playstyle when losing
```

---

## 🧠 Intelligence Modules

| Module | What It Detects |
|--------|-----------------|
| **Peek IQ** | Smart vs ego vs panic peeks |
| **Trade Discipline** | Perfect/late/missed trade opportunities |
| **Crosshair Discipline** | Head-level tracking, flick dependency |
| **Utility Intelligence** | Flash effectiveness, self-flash rate |
| **Rotation IQ** | Over-rotation, slow rotations |
| **Round Simulator** | Win probability impact of deaths |
| **Tilt Detector** | Mental degradation patterns |
| **Cheat Patterns** | Suspicious statistical anomalies |

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/Sacrilege_Engine.git
cd Sacrilege_Engine

# Setup
python3 -m venv venv
source venv/bin/activate
pip install demoparser2 pydantic pydantic-settings pandas fastapi uvicorn python-multipart

# Analyze a demo
PYTHONPATH=. python3 -c "
from pathlib import Path
from src.analysis_orchestrator import AnalysisOrchestrator
from src.output.feedback_generator import FeedbackGenerator

result = AnalysisOrchestrator().analyze(Path('your_demo.dem'))
for report in result.player_reports.values():
    print(FeedbackGenerator().format_report_text(report))
    break
"
```

---

## 📁 Project Structure

```
Sacrilege_Engine/
├── src/
│   ├── parser/          # Demo parsing (demoparser2)
│   ├── intelligence/    # 8 analysis modules
│   ├── world/           # Map geometry, visibility/LOS
│   ├── output/          # Feedback generation
│   └── api/             # FastAPI endpoints
├── docs/                # Architecture, schemas, wireframes
└── demo files/          # Test demos
```

---

## 🗺️ Supported Maps

- de_dust2, de_mirage, de_inferno
- de_ancient, de_nuke, de_overpass  
- de_anubis, de_vertigo, de_train

---

## 📊 Tech Stack

| Layer | Technology |
|-------|------------|
| Parser | `demoparser2` (Rust bindings) |
| Backend | Python 3.9+, FastAPI |
| Data | Pydantic, Pandas |
| World | Custom visibility/LOS system |

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System design, data flow |
| [Database Schema](docs/DATABASE_SCHEMA.md) | PostgreSQL tables |
| [Parsing Pipeline](docs/PARSING_PIPELINE.md) | Demo processing stages |
| [Intelligence Modules](docs/INTELLIGENCE_MODULES.md) | Module pseudo-code |
| [API Reference](docs/API_REFERENCE.md) | Endpoint documentation |
| [MVP Roadmap](docs/MVP_ROADMAP.md) | Development plan |

---

## ⚠️ License

**Proprietary Software** — See [LICENSE](LICENSE) for terms.

This software is proprietary and confidential. Unauthorized copying, modification, distribution, or use is strictly prohibited without explicit written permission.

---

## 🤝 Contributing

This is a proprietary project. Contributions require a signed Contributor License Agreement (CLA). Contact the maintainers for details.

---

<div align="center">

**Built for players who want to improve, not just see stats.**

</div>

# Sacrilege Engine - System Architecture

## Overview

Sacrilege Engine is a CS2 demo intelligence system that analyzes decision quality, not just mechanics.

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SACRILEGE ENGINE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────────────────────────────────────────┐   │
│  │   .dem FILE  │───▶│              DEMO PARSER ENGINE                   │   │
│  └──────────────┘    │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │   │
│                      │  │  Tick   │ │  Event  │ │ Player  │ │   Map   │ │   │
│                      │  │ Parser  │ │Extractor│ │ Tracker │ │ Loader  │ │   │
│                      │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ │   │
│                      └───────┼──────────┼──────────┼──────────┼────────┘   │
│                              │          │          │          │            │
│                              ▼          ▼          ▼          ▼            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    WORLD RECONSTRUCTION LAYER                         │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │  │
│  │  │  Visibility  │ │    Angle     │ │  Crosshair   │ │   Utility    │ │  │
│  │  │    Matrix    │ │   Exposure   │ │   Position   │ │ Trajectories │ │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    INTELLIGENCE MODULES                               │  │
│  │ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐          │  │
│  │ │  Peek IQ   │ │  Utility   │ │   Trade    │ │ Crosshair  │          │  │
│  │ │   Engine   │ │Intelligence│ │ Discipline │ │ Discipline │          │  │
│  │ └────────────┘ └────────────┘ └────────────┘ └────────────┘          │  │
│  │ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐          │  │
│  │ │ Rotation   │ │   Round    │ │    Tilt    │ │Soft-Cheat  │          │  │
│  │ │     IQ     │ │ Simulator  │ │  Detector  │ │  Patterns  │          │  │
│  │ └────────────┘ └────────────┘ └────────────┘ └────────────┘          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      OUTPUT PROCESSOR                                 │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                  │  │
│  │  │   Feedback   │ │   Report     │ │     API      │                  │  │
│  │  │  Generator   │ │   Builder    │ │   Endpoint   │                  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React + D3)                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │   Timeline   │ │   Heatmap    │ │  Decision    │ │    Team      │        │
│  │   Replay     │ │   Viewer     │ │    Graph     │ │ Synergy Web  │        │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘        │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
┌─────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  .dem   │────▶│   Parser    │────▶│    World     │────▶│ Intelligence│
│  File   │     │   Engine    │     │Reconstruction│     │   Modules   │
└─────────┘     └─────────────┘     └──────────────┘     └──────────────┘
                                                                │
                                                                ▼
┌─────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Frontend│◀────│     API     │◀────│    Report    │◀────│   Output    │
│   UI    │     │   Layer     │     │   Builder    │     │  Processor  │
└─────────┘     └─────────────┘     └──────────────┘     └──────────────┘
```

---

## Folder Structure

```
Sacrilege_Engine/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATABASE_SCHEMA.md
│   ├── API_REFERENCE.md
│   └── WIREFRAMES.md
│
├── src/
│   ├── __init__.py
│   │
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── demo_parser.py          # Main parser orchestrator
│   │   ├── tick_processor.py       # Tick-by-tick processing
│   │   ├── event_extractor.py      # Shot/hit/death/utility events
│   │   ├── player_tracker.py       # Position/velocity/angles
│   │   └── map_loader.py           # Map geometry + nav mesh
│   │
│   ├── world/
│   │   ├── __init__.py
│   │   ├── reconstruction.py       # State reconstruction
│   │   ├── visibility.py           # LOS raycasting
│   │   ├── angle_exposure.py       # Multi-angle exposure
│   │   └── utility_simulation.py   # Utility trajectories
│   │
│   ├── intelligence/
│   │   ├── __init__.py
│   │   ├── peek_iq.py              # Peek classification
│   │   ├── utility_intel.py        # Utility analysis
│   │   ├── trade_discipline.py     # Trade scoring
│   │   ├── crosshair_discipline.py # Aim discipline
│   │   ├── rotation_iq.py          # Rotation analysis
│   │   ├── round_simulator.py      # What-if scenarios
│   │   ├── tilt_detector.py        # Mental state detection
│   │   └── cheat_patterns.py       # Suspicious patterns
│   │
│   ├── output/
│   │   ├── __init__.py
│   │   ├── feedback_generator.py   # Actionable feedback
│   │   ├── report_builder.py       # Full report assembly
│   │   └── formatters.py           # JSON/HTML/PDF output
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py               # FastAPI endpoints
│   │   ├── schemas.py              # Pydantic models
│   │   └── middleware.py           # Auth, rate limiting
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py               # SQLAlchemy models
│   │   ├── crud.py                 # Database operations
│   │   └── migrations/             # Alembic migrations
│   │
│   └── utils/
│       ├── __init__.py
│       ├── math_utils.py           # Vector math, raycasting
│       ├── cs2_constants.py        # Game constants
│       └── logger.py               # Structured logging
│
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Timeline/
│   │   │   ├── Heatmap/
│   │   │   ├── DecisionGraph/
│   │   │   └── SynergyWeb/
│   │   ├── pages/
│   │   │   ├── Upload.tsx
│   │   │   ├── Analysis.tsx
│   │   │   └── Report.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   └── utils/
│   │       └── d3-helpers.ts
│   └── public/
│       └── maps/                   # Map radar images
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│       └── sample_demos/
│
├── scripts/
│   ├── download_maps.py
│   └── benchmark.py
│
├── config/
│   ├── settings.py
│   └── maps/                       # Map geometry JSON
│
├── requirements.txt
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Technology Stack

### Backend: Python 3.11+

**Why Python?**
- Rich ecosystem for data analysis (numpy, scipy, pandas)
- Excellent CS2 demo parsing libraries exist
- Fast prototyping, easy to iterate
- AsyncIO for concurrent processing

**Libraries:**
| Purpose | Library | Reason |
|---------|---------|--------|
| Demo Parsing | `demoparser2` | Native Rust bindings, fastest Python parser |
| API | `FastAPI` | Async, auto-docs, Pydantic validation |
| Database | `SQLAlchemy` + `asyncpg` | Async PostgreSQL access |
| Migrations | `Alembic` | Production-grade migrations |
| Vector Math | `numpy` | Vectorized operations for LOS |
| Caching | `Redis` | Session caching, task queues |
| Task Queue | `Celery` | Heavy demo processing |
| Logging | `structlog` | Structured JSON logs |

### Database: PostgreSQL 15

**Why PostgreSQL?**
- JSON support for flexible event storage
- Full-text search for querying events
- PostGIS for spatial queries (player positions)
- Excellent performance at scale

### Frontend: React 18 + TypeScript + D3.js

**Why This Stack?**
- React: Component model fits visualization needs
- TypeScript: Catch errors early, better DX
- D3.js: Industry standard for custom visualizations
- Vite: Fast dev server, minimal config

**Additional Libraries:**
| Purpose | Library |
|---------|---------|
| State | Zustand |
| Styling | CSS Modules + CSS Variables |
| HTTP | Axios |
| Charts | D3.js (custom) |
| Maps | Leaflet (for 2D position views) |

### Infrastructure

| Component | Technology |
|-----------|------------|
| Container | Docker |
| Orchestration | Docker Compose (dev), K8s (prod) |
| Reverse Proxy | Nginx |
| CI/CD | GitHub Actions |
| Monitoring | Prometheus + Grafana |

---

## Modular Design Principles

### 1. Plugin Architecture for Intelligence Modules

Each intelligence module implements a common interface:

```python
class IntelligenceModule(Protocol):
    name: str
    version: str
    
    def analyze(self, world_state: WorldState) -> ModuleResult:
        """Run analysis on reconstructed world state"""
        ...
    
    def get_feedback(self, result: ModuleResult) -> list[Feedback]:
        """Generate actionable feedback from results"""
        ...
```

### 2. Event-Driven Processing

```python
# Events flow through pipeline
DemoLoaded -> TickProcessed -> EventExtracted -> WorldReconstructed -> AnalysisComplete
```

### 3. Separation of Concerns

- **Parser**: Only extracts raw data
- **World**: Only reconstructs state
- **Intelligence**: Only analyzes patterns
- **Output**: Only formats results

### 4. Configuration-Driven

All thresholds and weights are configurable:

```python
# config/settings.py
class PeekIQConfig:
    pre_aim_angle_threshold: float = 15.0  # degrees
    info_based_recent_sound_ms: int = 2000
    trade_available_distance: float = 800.0
```

---

## CS2 Update Resilience

### Strategy

1. **Version Detection**: Parse demo header for game version
2. **Schema Versioning**: Separate parsing schemas per version
3. **Abstraction Layer**: Internal models don't depend on demo format
4. **Graceful Degradation**: Missing fields don't crash analysis

```python
class DemoVersionAdapter:
    """Adapts different CS2 demo versions to unified format"""
    
    ADAPTERS = {
        "13998": CS2Adapter_13998,
        "14000": CS2Adapter_14000,
        # Add new versions here
    }
```

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Demo parse time | < 30s for 45-min demo |
| World reconstruction | < 100ms per round |
| Full analysis | < 2 min per demo |
| Memory usage | < 4GB peak |
| API response | < 200ms for cached |

---

## Security Considerations

1. **Demo Validation**: Verify file headers, reject malformed
2. **Size Limits**: Max 500MB per demo upload
3. **Rate Limiting**: 10 demos/hour per user
4. **Input Sanitization**: All demo data treated as untrusted
5. **No Execution**: Demo files are data only, never executed

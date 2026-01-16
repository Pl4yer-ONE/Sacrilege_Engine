# Sacrilege Engine - MVP Roadmap

## MVP Definition

**Goal**: Functional demo analysis that proves decision-quality feedback.

**Scope**: Single player analysis from one demo. No team features. No simulation.

---

## MVP Features

### In Scope
- Demo upload + validation
- Tick parsing
- Event extraction (kills, deaths, utility)
- Basic visibility checks
- 3 intelligence modules: Peek IQ, Trade Discipline, Crosshair Discipline
- Top 3 mistakes output
- Basic heatmap
- Timeline view

### Out of Scope (Post-MVP)
- Round simulator
- Team synergy analysis
- Soft-cheat detection
- Full tilt detector
- Multi-demo tracking
- User accounts
- API rate limiting

---

## Weekly Milestones

### Week 1: Foundation

**Goal**: Parse any CS2 demo, extract events.

| Day | Deliverable |
|-----|-------------|
| 1-2 | Project setup: Python env, FastAPI skeleton, DB schema |
| 3-4 | Demo validation + header parsing |
| 5-6 | Tick processor, player state extraction |
| 7   | Event extractor (kills, deaths, shots) |

**Exit Criteria**:
- Upload .dem → JSON of all kills/deaths
- ≤30s parse time for 45-min demo

---

### Week 2: World Reconstruction

**Goal**: Visibility matrix at any tick.

| Day | Deliverable |
|-----|-------------|
| 1-2 | Map geometry loader (dust2, mirage) |
| 3-4 | BSP tree for raycasting |
| 5   | Visibility computation |
| 6-7 | Angle exposure calculation |

**Exit Criteria**:
- Query: "At tick X, who can see player Y?"
- Result in <50ms

---

### Week 3: Intelligence Modules (Part 1)

**Goal**: Peek IQ + Crosshair Discipline working.

| Day | Deliverable |
|-----|-------------|
| 1-2 | Peek event detection |
| 3-4 | Peek IQ classification logic |
| 5   | Crosshair tracking per tick |
| 6-7 | Discipline scoring |

**Exit Criteria**:
- Every peek classified (smart/ego/panic/etc)
- Crosshair discipline % computed

---

### Week 4: Intelligence Modules (Part 2)

**Goal**: Trade Discipline + Feedback Generator.

| Day | Deliverable |
|-----|-------------|
| 1-2 | Trade opportunity detection |
| 3-4 | Trade classification (perfect/late/missed) |
| 5-6 | Feedback generator (top 3 mistakes) |
| 7   | Output formatting (JSON/HTML) |

**Exit Criteria**:
- Every death has trade analysis
- Top 3 mistakes ranked by severity

---

### Week 5: Visualization

**Goal**: Timeline + Heatmap.

| Day | Deliverable |
|-----|-------------|
| 1-2 | React project setup |
| 3-4 | Timeline component |
| 5-6 | Heatmap component |
| 7   | Integration with API |

**Exit Criteria**:
- Timeline shows all events
- Heatmap renders death positions

---

### Week 6: Integration + Polish

**Goal**: End-to-end flow working.

| Day | Deliverable |
|-----|-------------|
| 1-2 | Upload flow |
| 3-4 | Processing status |
| 5-6 | Report page |
| 7   | Bug fixes, performance |

**Exit Criteria**:
- User uploads demo → sees report
- Full flow <2 minutes

---

## Testing Strategy

### Unit Tests

```
tests/unit/
├── parser/
│   ├── test_demo_validator.py
│   ├── test_tick_processor.py
│   └── test_event_extractor.py
├── world/
│   ├── test_visibility.py
│   └── test_map_loader.py
├── intelligence/
│   ├── test_peek_iq.py
│   ├── test_trade_discipline.py
│   └── test_crosshair_discipline.py
└── output/
    └── test_feedback_generator.py
```

**Coverage Target**: 80%

### Integration Tests

```
tests/integration/
├── test_full_pipeline.py       # Upload → Report
├── test_api_endpoints.py       # All routes
└── test_database_operations.py # CRUD ops
```

### Fixtures

```
tests/fixtures/
├── sample_demos/
│   ├── dust2_short.dem     # 5-round demo
│   ├── mirage_full.dem     # Full match
│   └── corrupted.dem       # For error handling
└── expected_outputs/
    ├── dust2_short_events.json
    └── dust2_short_analysis.json
```

### Manual Testing Checklist

- [ ] Upload 10+ different demos
- [ ] Verify each map loads correctly
- [ ] Compare visibility results to in-game replay
- [ ] Validate trade classifications against manual review
- [ ] Check heatmap accuracy against radar

---

## Performance Optimization

### Phase 1: Baseline (Week 1-2)
- Measure initial performance
- Profile hot paths
- Set benchmarks

### Phase 2: Critical Path (Week 3-4)
- Optimize visibility raycasting (BSP tree)
- Parallelize event extraction
- Chunk tick processing

### Phase 3: Caching (Week 5-6)
- Cache visibility per tick
- Cache map geometry
- Redis for API responses

### Targets

| Operation | Target | Current |
|-----------|--------|---------|
| Demo parse | <30s | TBD |
| Visibility query | <50ms | TBD |
| Full analysis | <2min | TBD |
| API response | <200ms | TBD |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| CS2 demo format changes | Version detection + adapter pattern |
| Map geometry unavailable | Start with 2 maps, add more incrementally |
| Performance bottlenecks | Profile early, optimize incrementally |
| Visibility calculation complex | Start with 2D, upgrade to 3D later |

---

## Post-MVP Roadmap

### v1.1 (Week 7-8)
- Utility Intelligence module
- Rotation IQ module
- More maps (inferno, ancient, anubis)

### v1.2 (Week 9-10)
- Tilt Detector
- Decision graph visualization
- Team synergy web

### v1.3 (Week 11-12)
- Round Simulator (what-if)
- Multi-demo tracking
- User accounts

### v2.0 (Future)
- Soft-cheat pattern detection
- Coach/analyst views
- API access for third parties

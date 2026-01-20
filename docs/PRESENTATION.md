# SACRILEGE ENGINE
## A Real-Time CS2 Demo Analysis System with Blame Attribution

---

### Conference Presentation — IEEE Format

**Author:** Pl4yer-ONE  
**Contact:** mahadevan.rajeev27@gmail.com  
**Repository:** github.com/Pl4yer-ONE/Sacrilege_Engine

---

## Slide 1: Title

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                    SACRILEGE ENGINE                          ║
║                                                              ║
║     A Real-Time CS2 Demo Analysis System                     ║
║     with Blame Attribution                                   ║
║                                                              ║
║     ─────────────────────────────────────────                ║
║                                                              ║
║     Author: Pl4yer-ONE                                       ║
║     Email: mahadevan.rajeev27@gmail.com                      ║
║                                                              ║
║     January 2026                                             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Slide 2: Problem Statement

### Current CS2 Analysis Tools Are Insufficient

| Traditional Tools | Sacrilege Engine |
|:------------------|:-----------------|
| ❌ Team-level stats only | ✅ Individual death analysis |
| ❌ Post-match summaries | ✅ Real-time feedback |
| ❌ "You died 15 times" | ✅ **Why** you died 15 times |
| ❌ Abstract K/D ratios | ✅ Blame scores per death |

> **Gap:** No tool assigns accountability to individual deaths with tactical reasoning.

---

## Slide 3: Solution Overview

### Sacrilege Engine: Core Features

```
┌─────────────────────────────────────────────────────────┐
│                   SACRILEGE ENGINE                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │   PARSER    │───▶│  ANALYZER   │───▶│   VIEWER    │ │
│  │ (demoparser2)│   │(DeathAnalyzer)│  │(RadarReplayer)│ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│                                                         │
│  • Parse .dem files    • 15 mistake     • Live radar   │
│  • Extract kills         categories     • Rankings     │
│  • Track positions     • Blame scores   • Kill feed    │
│                        • S-F grades                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Slide 4: Mistake Classification System

### 15 Tactical Mistake Categories

| Severity | Category | Description |
|:--------:|:---------|:------------|
| **5** | ISOLATED | Died alone, no support possible |
| **5** | CROSSFIRE | Exposed to multiple angles |
| **5** | SOLO_PUSH | Pushed alone into enemy territory |
| **4** | NO_TRADE | Teammate close but didn't trade |
| **4** | WIDE_PEEK | Over-extended peek |
| **3** | FLASHED | Killed while blinded |
| **3** | OUTNUMBERED | Took unfavorable fight |
| **2** | FIRST_CONTACT | Entry death (acceptable) |
| **1** | FAIR_DUEL | Lost aim battle |
| **1** | TRADED | At least got traded |

---

## Slide 5: Blame Score Algorithm

### Mathematical Model

```
Blame Score = (Severity × 20) + Modifiers

Modifiers:
  • Isolation (distance > 1000u): +10
  • Multiple enemies (≥3):       -10
  • Was traded:                  -15
  • Was flashed:                  -5

Final Score: Clamped to [0, 100]
```

### Example Calculation

```
Death: Player isolated in crossfire

Severity: 5 (CRITICAL)
Base:     5 × 20 = 100

Modifiers:
  + 10 (isolated, distance = 1500u)
  - 10 (facing 3 enemies)
  
Final:    min(100, max(0, 100)) = 100% blame
```

---

## Slide 6: Performance Grading

### S-F Grade System

```
Performance Score = (K/D × 40) - (Avg Blame × 0.4) + 20

Grade Thresholds:
  S: ≥ 80    "Elite"
  A: ≥ 65    "Strong"
  B: ≥ 50    "Average"
  C: ≥ 35    "Below Average"
  D: ≥ 20    "Poor"
  F: < 20    "Liability"
```

| Grade | Color | Meaning |
|:-----:|:-----:|:--------|
| **S** | 🟡 Gold | Exceptional performance |
| **A** | 🟢 Green | Strong contributor |
| **B** | 🔵 Blue | Solid player |
| **C** | ⚪ Silver | Room for improvement |
| **D** | 🟠 Orange | Struggling |
| **F** | 🔴 Red | Team liability |

---

## Slide 7: System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        USER INPUT                            │
│                     (.dem file path)                         │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                     DEMO PARSER                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│  │   Header   │  │   Kills    │  │ Positions  │             │
│  │  (map,     │  │  (events,  │  │  (ticks,   │             │
│  │  server)   │  │  weapons)  │  │  players)  │             │
│  └────────────┘  └────────────┘  └────────────┘             │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   DEATH ANALYZER                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  For each kill:                                         ││
│  │    1. Get victim position                               ││
│  │    2. Calculate teammate distances                      ││
│  │    3. Count nearby enemies                              ││
│  │    4. Check utility state (flash, molly)                ││
│  │    5. Classify mistakes                                 ││
│  │    6. Compute blame score                               ││
│  └─────────────────────────────────────────────────────────┘│
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   RADAR REPLAYER                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Player  │  │   Kill   │  │  Stats   │  │ Rankings │    │
│  │  Cards   │  │   Feed   │  │  Panel   │  │  Panel   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└──────────────────────────────────────────────────────────────┘
```

---

## Slide 8: UI Components

### Premium Glassmorphism Design

| Component | Features |
|:----------|:---------|
| **Header** | Animated cyan logo, playback state |
| **Player Cards** | Health bars, equipment, weapons |
| **Radar Map** | 8 competitive maps, utility overlays |
| **Kill Feed** | Death reason popups with blame % |
| **Statistics** | Round kills, team HP, equipment |
| **Rankings** | Live S-F grades with progress bars |
| **Legend** | Smoke/Fire/Flash/HE indicators |

### Color Palette

```
Background:  #060810 (Deep space black)
CT:          #3C8CFF (Neon blue)
T:           #FFAA28 (Neon orange)
Accent:      #00DCFF (Cyan)
Grade S:     #FFD700 (Gold)
Grade A:     #64FF96 (Green)
Grade F:     #FF4646 (Red)
```

---

## Slide 9: Validation Results

### Test Dataset

| Metric | Value |
|:-------|:------|
| Maps Tested | 4 (Dust2, Ancient, Overpass, Mirage) |
| Total Deaths | 330 |
| Rounds Analyzed | 80+ |
| Processing Time | ~3 seconds per demo |

### Mistake Distribution

```
CROSSFIRE:   59% ████████████████████████░░░░░░░░░░░░░░░░
ISOLATED:    32% ████████████████░░░░░░░░░░░░░░░░░░░░░░░░
NO_TRADE:    15% ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
OUTNUMBERED: 12% ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
SOLO_PUSH:    8% ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
```

---

## Slide 10: Key Contributions

### Novel Contributions

1. **Death-Level Blame Attribution**
   - First system to assign accountability scores to individual deaths
   - 15-category mistake classification hierarchy

2. **Real-Time Performance Grading**
   - S-F grades computed during demo playback
   - Dynamic rankings that update with each kill

3. **Integrated Visualization**
   - Radar overlay with live player positions
   - Death popups with tactical explanations

4. **Premium UI Design**
   - 60+ color definitions with neon accents
   - Glassmorphism-inspired theme

---

## Slide 11: Future Work

### Planned Enhancements

| Phase | Feature | Description |
|:-----:|:--------|:------------|
| **1** | ML Integration | Train on pro matches |
| **2** | Team Coordination | Blame team failures |
| **3** | Web Dashboard | Browser-based access |
| **4** | Voice Coach | Real-time audio feedback |
| **5** | Pro Benchmarks | Compare to HLTV stats |

---

## Slide 12: Conclusion

### Summary

> **Sacrilege Engine** provides what traditional analysis lacks:  
> **Actionable, individual-level feedback** through blame attribution.

### Key Takeaways

✅ **15 mistake categories** for precise classification  
✅ **Blame scores (0-100%)** per death  
✅ **S-F grades** for performance ranking  
✅ **Real-time visualization** during demo playback  
✅ **Premium UI** with glassmorphism design  

---

## Slide 13: Demo

### Live Demonstration

```
Controls:
  SPACE     - Play / Pause
  ← →       - Seek ±5 seconds
  ↑ ↓       - Adjust playback speed
  E / R     - Previous / Next round
  F12       - Screenshot
  H         - Help overlay
  F         - Fullscreen
```

**Repository:** github.com/Pl4yer-ONE/Sacrilege_Engine

---

## Slide 14: Q&A

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                      QUESTIONS?                              ║
║                                                              ║
║     ─────────────────────────────────────────                ║
║                                                              ║
║     GitHub:  github.com/Pl4yer-ONE/Sacrilege_Engine          ║
║     Email:   mahadevan.rajeev27@gmail.com                    ║
║                                                              ║
║     ─────────────────────────────────────────                ║
║                                                              ║
║            "The truth hurts. Sacrilege delivers it."         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## References

1. Valve Corporation, "Counter-Strike 2," 2023.
2. demoparser2, "CS2 Demo Parser Library," GitHub, 2024.
3. boltobserv, "CS2 Radar Map Overlays," GitHub, 2023.

---

*Presentation created for Sacrilege Engine v1.3.0*

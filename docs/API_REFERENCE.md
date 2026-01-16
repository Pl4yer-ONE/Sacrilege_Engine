# Sacrilege Engine - API Reference

## Base URL

```
Production: https://api.sacrilege.engine/v1
Development: http://localhost:8000/v1
```

---

## Endpoints

### Demo Upload

**POST** `/demos/upload`

Upload a CS2 demo file for analysis.

```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -F "file=@match.dem" \
  https://api.sacrilege.engine/v1/demos/upload
```

**Response**
```json
{
  "demo_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "estimated_time_seconds": 90
}
```

---

### Demo Status

**GET** `/demos/{demo_id}/status`

Check processing status.

```json
{
  "demo_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress_percent": 47,
  "current_stage": "analyzing_trade_discipline",
  "stages_complete": ["validation", "parsing", "visibility"],
  "stages_pending": ["feedback_generation"]
}
```

---

### Analysis Report

**GET** `/demos/{demo_id}/report`

Get full analysis report.

```json
{
  "demo_id": "550e8400-e29b-41d4-a716-446655440000",
  "map": "de_dust2",
  "score": "16-12",
  "player": {
    "steam_id": "76561198012345678",
    "name": "PlayerName",
    "team": "ct"
  },
  "top_mistakes": [
    {
      "rank": 1,
      "category": "tactical",
      "title": "Missed trades at Long A",
      "description": "Your teammate died 3x at Long with you 400 units away.",
      "rounds": [5, 9],
      "severity": "critical",
      "fix": "Position closer or don't play duo."
    }
  ],
  "fixes": {
    "mechanical": "Pre-aim is 12° off average. Practice crosshair placement.",
    "tactical": "Over-rotate by 2.1s average. Trust your anchor.",
    "mental": "Solo pushes increased 3x after R8. Tilt detected."
  },
  "scores": {
    "peek_iq": 68,
    "trade_discipline": 42,
    "crosshair_discipline": 71,
    "rotation_iq": 55
  }
}
```

---

### Round Data

**GET** `/demos/{demo_id}/rounds/{round_number}`

Get detailed round data.

```json
{
  "round_number": 5,
  "winner": "t",
  "win_reason": "elimination",
  "tick_range": [12400, 19800],
  "events": [
    {
      "tick": 14200,
      "type": "kill",
      "attacker": "76561198012345678",
      "victim": "76561198087654321",
      "weapon": "ak47",
      "headshot": true
    }
  ],
  "player_analysis": {
    "peek_classifications": [
      {
        "tick": 14100,
        "classification": "ego",
        "pre_aim_score": 0.3,
        "trade_available": false
      }
    ]
  }
}
```

---

### Heatmap Data

**GET** `/demos/{demo_id}/heatmap`

Get heatmap data points.

**Query Params**:
- `event_type`: deaths | kills | all
- `side`: ct | t | both
- `round_start`: 1
- `round_end`: 16

```json
{
  "map": "de_dust2",
  "bounds": {
    "min_x": -2476,
    "max_x": 2108,
    "min_y": -1250,
    "max_y": 3239
  },
  "points": [
    {
      "x": -1234,
      "y": 2567,
      "weight": 3,
      "event_type": "death",
      "rounds": [5, 9, 12]
    }
  ]
}
```

---

### Timeline Data

**GET** `/demos/{demo_id}/timeline`

Get timeline events.

```json
{
  "rounds": [
    {
      "number": 1,
      "start_tick": 1200,
      "end_tick": 8400,
      "events": [
        {
          "tick": 3400,
          "type": "mistake",
          "category": "ego_peek",
          "severity": "major"
        }
      ]
    }
  ]
}
```

---

## Error Responses

```json
{
  "error": {
    "code": "DEMO_TOO_LARGE",
    "message": "Demo file exceeds 500MB limit",
    "details": {
      "max_size_mb": 500,
      "actual_size_mb": 612
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| DEMO_NOT_FOUND | 404 | Demo ID doesn't exist |
| DEMO_TOO_LARGE | 413 | File exceeds size limit |
| INVALID_FORMAT | 400 | Not a valid CS2 demo |
| PROCESSING_FAILED | 500 | Analysis failed |
| RATE_LIMITED | 429 | Too many requests |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| Upload | 10/hour |
| Status | 60/minute |
| Report | 30/minute |
| Heatmap | 30/minute |

# Sacrilege Engine - Database Schema

## Overview

PostgreSQL 15 with PostGIS extension for spatial queries.

---

## Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    demos     │───┬──▶│    rounds    │───┬──▶│    events    │
└──────────────┘   │   └──────────────┘   │   └──────────────┘
                   │                      │
                   │   ┌──────────────┐   │   ┌──────────────┐
                   ├──▶│   players    │   └──▶│player_states │
                   │   └──────────────┘       └──────────────┘
                   │
                   │   ┌──────────────┐       ┌──────────────┐
                   └──▶│  analyses    │───┬──▶│  feedbacks   │
                       └──────────────┘   │   └──────────────┘
                                          │
                                          │   ┌──────────────┐
                                          └──▶│   scores     │
                                              └──────────────┘
```

---

## Tables

### demos

Central record for each parsed demo file.

```sql
CREATE TABLE demos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_hash       VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 of file
    file_name       VARCHAR(255) NOT NULL,
    file_size       BIGINT NOT NULL,
    
    -- Game metadata
    map_name        VARCHAR(64) NOT NULL,
    game_version    VARCHAR(32),
    match_date      TIMESTAMP WITH TIME ZONE,
    server_name     VARCHAR(255),
    
    -- Match result
    team_ct_score   SMALLINT,
    team_t_score    SMALLINT,
    winner          VARCHAR(16),  -- 'ct', 't', 'draw'
    
    -- Processing status
    status          VARCHAR(32) DEFAULT 'pending',  -- pending, processing, complete, failed
    error_message   TEXT,
    
    -- Metadata
    uploaded_by     UUID REFERENCES users(id),
    created_at      TIMESTAMP DEFAULT NOW(),
    processed_at    TIMESTAMP,
    
    -- Demo header info
    tick_rate       REAL,
    duration_ticks  INTEGER,
    duration_secs   REAL,
    
    CONSTRAINT valid_status CHECK (status IN ('pending', 'processing', 'complete', 'failed'))
);

CREATE INDEX idx_demos_status ON demos(status);
CREATE INDEX idx_demos_map ON demos(map_name);
CREATE INDEX idx_demos_date ON demos(match_date DESC);
```

### players

Player information per demo.

```sql
CREATE TABLE players (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demo_id         UUID NOT NULL REFERENCES demos(id) ON DELETE CASCADE,
    
    -- Identity
    steam_id        VARCHAR(32) NOT NULL,
    name            VARCHAR(64) NOT NULL,
    
    -- Team assignment
    team            VARCHAR(16) NOT NULL,  -- 'ct', 't'
    team_number     SMALLINT,  -- 2 = T, 3 = CT
    
    -- Final stats
    kills           INTEGER DEFAULT 0,
    deaths          INTEGER DEFAULT 0,
    assists         INTEGER DEFAULT 0,
    headshot_pct    REAL,
    adr             REAL,
    
    UNIQUE(demo_id, steam_id)
);

CREATE INDEX idx_players_demo ON players(demo_id);
CREATE INDEX idx_players_steam ON players(steam_id);
```

### rounds

Round-level data.

```sql
CREATE TABLE rounds (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demo_id         UUID NOT NULL REFERENCES demos(id) ON DELETE CASCADE,
    
    round_number    SMALLINT NOT NULL,
    
    -- Timing
    start_tick      INTEGER NOT NULL,
    end_tick        INTEGER NOT NULL,
    freeze_end_tick INTEGER,
    
    -- Outcome
    winner          VARCHAR(16),  -- 'ct', 't'
    win_reason      VARCHAR(32),  -- 'bomb_defused', 'elimination', 'time', 'bomb_exploded'
    
    -- Economy
    ct_equipment    INTEGER,
    t_equipment     INTEGER,
    ct_economy      INTEGER,
    t_economy       INTEGER,
    
    UNIQUE(demo_id, round_number)
);

CREATE INDEX idx_rounds_demo ON rounds(demo_id);
```

### events

All game events (shots, deaths, utility, etc).

```sql
CREATE TABLE events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id        UUID NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    demo_id         UUID NOT NULL REFERENCES demos(id) ON DELETE CASCADE,
    
    tick            INTEGER NOT NULL,
    event_type      VARCHAR(32) NOT NULL,
    
    -- Actor/Target
    player_id       UUID REFERENCES players(id),
    target_id       UUID REFERENCES players(id),  -- For damage/kill events
    
    -- Position data
    position        GEOMETRY(POINTZ, 0),  -- x, y, z
    target_position GEOMETRY(POINTZ, 0),
    
    -- View angles
    view_x          REAL,  -- pitch
    view_y          REAL,  -- yaw
    
    -- Event-specific data (flexible JSON)
    data            JSONB NOT NULL DEFAULT '{}',
    
    CONSTRAINT valid_event_type CHECK (event_type IN (
        'shot', 'hit', 'kill', 'death', 'damage',
        'flash', 'smoke', 'molotov', 'he_grenade', 'decoy',
        'bomb_plant', 'bomb_defuse', 'bomb_explode',
        'round_start', 'round_end', 'freeze_end',
        'footstep', 'weapon_fire_sound', 'reload_sound'
    ))
);

CREATE INDEX idx_events_round ON events(round_id);
CREATE INDEX idx_events_tick ON events(tick);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_player ON events(player_id);
CREATE INDEX idx_events_position ON events USING GIST(position);
```

### player_states

Per-tick player state snapshots (sampled, not every tick).

```sql
CREATE TABLE player_states (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id        UUID NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    player_id       UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    
    tick            INTEGER NOT NULL,
    
    -- Position/Movement
    position        GEOMETRY(POINTZ, 0),
    velocity        REAL,  -- magnitude
    velocity_dir    REAL,  -- direction in degrees
    
    -- View
    view_x          REAL,
    view_y          REAL,
    
    -- State
    health          SMALLINT,
    armor           SMALLINT,
    has_helmet      BOOLEAN,
    has_defuser     BOOLEAN,
    
    -- Equipment
    active_weapon   VARCHAR(32),
    money           INTEGER,
    equipment_value INTEGER,
    
    -- Visibility (computed)
    visible_enemies UUID[],  -- Array of player IDs this player can see
    is_flashed      BOOLEAN DEFAULT FALSE,
    flash_duration  REAL,
    
    UNIQUE(round_id, player_id, tick)
);

-- Partition by round for performance
CREATE INDEX idx_player_states_round ON player_states(round_id);
CREATE INDEX idx_player_states_tick ON player_states(tick);
CREATE INDEX idx_player_states_position ON player_states USING GIST(position);
```

### analyses

Analysis results per demo.

```sql
CREATE TABLE analyses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demo_id         UUID NOT NULL REFERENCES demos(id) ON DELETE CASCADE,
    player_id       UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    
    -- Version tracking
    engine_version  VARCHAR(16) NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW(),
    
    -- Processing
    status          VARCHAR(32) DEFAULT 'pending',
    processing_time_ms INTEGER,
    
    UNIQUE(demo_id, player_id, engine_version)
);
```

### scores

Computed scores per intelligence module.

```sql
CREATE TABLE scores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id     UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    
    module_name     VARCHAR(64) NOT NULL,  -- 'peek_iq', 'utility_intel', etc.
    
    -- Scores (0-100 scale)
    overall_score   REAL NOT NULL,
    
    -- Component scores (JSON for flexibility)
    components      JSONB NOT NULL DEFAULT '{}',
    
    -- Round-by-round breakdown
    round_scores    JSONB NOT NULL DEFAULT '[]',
    
    UNIQUE(analysis_id, module_name)
);

CREATE INDEX idx_scores_analysis ON scores(analysis_id);
CREATE INDEX idx_scores_module ON scores(module_name);
```

### feedbacks

Actionable feedback items.

```sql
CREATE TABLE feedbacks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id     UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    
    -- Classification
    category        VARCHAR(32) NOT NULL,  -- 'mechanical', 'tactical', 'mental'
    severity        VARCHAR(16) NOT NULL,  -- 'critical', 'major', 'minor'
    priority        SMALLINT NOT NULL,  -- 1-10, 1 = most important
    
    -- Content
    title           VARCHAR(255) NOT NULL,
    description     TEXT NOT NULL,
    
    -- Evidence
    round_number    SMALLINT,
    tick            INTEGER,
    evidence_data   JSONB DEFAULT '{}',  -- Screenshots, clips location, etc.
    
    -- Module source
    source_module   VARCHAR(64) NOT NULL
);

CREATE INDEX idx_feedbacks_analysis ON feedbacks(analysis_id);
CREATE INDEX idx_feedbacks_priority ON feedbacks(priority);
```

### peek_analyses

Detailed peek analysis (denormalized for query performance).

```sql
CREATE TABLE peek_analyses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id     UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    round_id        UUID NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    
    tick            INTEGER NOT NULL,
    
    -- Peek details
    peek_type       VARCHAR(32) NOT NULL,  -- 'smart', 'forced', 'ego', 'panic', 'info'
    
    -- Metrics
    pre_aimed       BOOLEAN,
    pre_aim_angle   REAL,  -- Angle off from enemy head
    info_based      BOOLEAN,
    recent_sound_cue BOOLEAN,
    trade_available BOOLEAN,
    trade_distance  REAL,
    
    -- Outcome
    resulted_in_kill BOOLEAN,
    resulted_in_death BOOLEAN,
    damage_dealt    INTEGER,
    damage_taken    INTEGER,
    
    -- Position context
    position        GEOMETRY(POINTZ, 0),
    target_position GEOMETRY(POINTZ, 0),
    
    CONSTRAINT valid_peek_type CHECK (peek_type IN ('smart', 'forced', 'ego', 'panic', 'info'))
);

CREATE INDEX idx_peek_analyses_analysis ON peek_analyses(analysis_id);
CREATE INDEX idx_peek_analyses_type ON peek_analyses(peek_type);
```

### utility_uses

Utility usage tracking.

```sql
CREATE TABLE utility_uses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id     UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    round_id        UUID NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    
    tick            INTEGER NOT NULL,
    utility_type    VARCHAR(32) NOT NULL,  -- 'flash', 'smoke', 'molly', 'he'
    
    -- Position
    throw_position  GEOMETRY(POINTZ, 0),
    land_position   GEOMETRY(POINTZ, 0),
    
    -- Effectiveness
    enemies_affected INTEGER DEFAULT 0,
    teammates_affected INTEGER DEFAULT 0,
    
    -- Flash specific
    flash_duration_avg REAL,
    flash_full_blinds INTEGER,
    flash_self_blind BOOLEAN,
    flash_team_blind INTEGER,
    
    -- Smoke specific
    smoke_blocks_sightline BOOLEAN,
    smoke_timing_vs_push REAL,  -- seconds before/after enemy push
    
    -- Molly specific
    molly_denial_time REAL,  -- seconds of area denial
    molly_damage_dealt INTEGER,
    
    -- ROI score
    utility_roi     REAL  -- 0-100
);

CREATE INDEX idx_utility_uses_analysis ON utility_uses(analysis_id);
CREATE INDEX idx_utility_uses_type ON utility_uses(utility_type);
```

### trade_events

Trade opportunity tracking.

```sql
CREATE TABLE trade_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id     UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    round_id        UUID NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    
    death_tick      INTEGER NOT NULL,
    victim_id       UUID NOT NULL REFERENCES players(id),
    killer_id       UUID NOT NULL REFERENCES players(id),
    
    -- Trade analysis
    trade_possible  BOOLEAN NOT NULL,
    trade_happened  BOOLEAN DEFAULT FALSE,
    trade_tick      INTEGER,
    trade_delay_ms  INTEGER,  -- Reaction time
    
    -- Positions
    victim_position GEOMETRY(POINTZ, 0),
    killer_position GEOMETRY(POINTZ, 0),
    nearest_teammate_id UUID REFERENCES players(id),
    nearest_teammate_distance REAL,
    
    -- Teammate state
    teammate_crosshair_on_enemy BOOLEAN,
    teammate_was_flashed BOOLEAN,
    teammate_was_looking BOOLEAN,
    
    -- Classification
    trade_classification VARCHAR(32),  -- 'perfect', 'late', 'missed', 'impossible'
    
    CONSTRAINT valid_classification CHECK (trade_classification IN ('perfect', 'late', 'missed', 'impossible'))
);

CREATE INDEX idx_trade_events_analysis ON trade_events(analysis_id);
```

---

## Views

### v_player_summary

Player performance summary view.

```sql
CREATE VIEW v_player_summary AS
SELECT 
    p.id,
    p.demo_id,
    p.steam_id,
    p.name,
    p.team,
    p.kills,
    p.deaths,
    p.assists,
    p.headshot_pct,
    p.adr,
    
    -- Aggregated scores
    AVG(s.overall_score) FILTER (WHERE s.module_name = 'peek_iq') as peek_iq_score,
    AVG(s.overall_score) FILTER (WHERE s.module_name = 'utility_intel') as utility_score,
    AVG(s.overall_score) FILTER (WHERE s.module_name = 'trade_discipline') as trade_score,
    AVG(s.overall_score) FILTER (WHERE s.module_name = 'crosshair_discipline') as crosshair_score,
    AVG(s.overall_score) FILTER (WHERE s.module_name = 'rotation_iq') as rotation_score,
    
    -- Feedback counts
    COUNT(f.id) FILTER (WHERE f.severity = 'critical') as critical_issues,
    COUNT(f.id) FILTER (WHERE f.severity = 'major') as major_issues
    
FROM players p
LEFT JOIN analyses a ON a.player_id = p.id
LEFT JOIN scores s ON s.analysis_id = a.id
LEFT JOIN feedbacks f ON f.analysis_id = a.id
GROUP BY p.id;
```

---

## Indexes Strategy

```sql
-- B-tree for equality/range queries
CREATE INDEX idx_events_demo_tick ON events(demo_id, tick);
CREATE INDEX idx_player_states_composite ON player_states(round_id, tick, player_id);

-- GiST for spatial queries
CREATE INDEX idx_events_position_gist ON events USING GIST(position);
CREATE INDEX idx_player_states_position_gist ON player_states USING GIST(position);

-- GIN for JSONB queries
CREATE INDEX idx_events_data_gin ON events USING GIN(data);
CREATE INDEX idx_scores_components_gin ON scores USING GIN(components);

-- Partial indexes for common queries
CREATE INDEX idx_events_kills ON events(tick) WHERE event_type = 'kill';
CREATE INDEX idx_events_deaths ON events(tick) WHERE event_type = 'death';
```

---

## Migration Strategy

Using Alembic for migrations:

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Run migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

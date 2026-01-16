# Sacrilege Engine - Intelligence Modules

## Module Interface

All intelligence modules implement this interface:

```python
class IntelligenceModule(Protocol):
    name: str
    version: str
    
    def analyze(self, context: AnalysisContext) -> ModuleResult:
        ...
    
    def generate_feedback(self, result: ModuleResult) -> list[Feedback]:
        ...
```

---

## Module A: Peek IQ Engine

### Purpose
Classify every peek/fight engagement to measure decision quality.

### Classification Logic

```python
class PeekClassifier:
    # Thresholds
    PRE_AIM_ANGLE_THRESHOLD = 15.0  # degrees off target
    RECENT_SOUND_WINDOW = 2000     # ms
    TRADE_AVAILABLE_DISTANCE = 800  # units
    
    def classify_peek(self, peek: PeekEvent, context: WorldState) -> PeekClassification:
        scores = {
            'pre_aimed': self.score_pre_aim(peek, context),
            'info_based': self.score_info(peek, context),
            'trade_available': self.score_trade_setup(peek, context),
            'timing': self.score_timing(peek, context),
        }
        
        # Decision tree
        if scores['pre_aimed'] > 0.8 and scores['trade_available'] > 0.7:
            return PeekClassification.SMART
        
        if scores['info_based'] > 0.6:
            return PeekClassification.INFO_BASED
        
        if self.is_forced_by_situation(peek, context):
            return PeekClassification.FORCED
        
        if self.is_ego_peek(peek, context):
            return PeekClassification.EGO
        
        if self.is_panic_peek(peek, context):
            return PeekClassification.PANIC
        
        return PeekClassification.NEUTRAL
    
    def score_pre_aim(self, peek: PeekEvent, context: WorldState) -> float:
        """How well crosshair was placed before peek."""
        enemy = context.get_player(peek.target_id)
        
        # Angle from crosshair to enemy head before peek
        angle_offset = self.compute_angle_offset(
            peek.view_angles_before,
            peek.position_before,
            enemy.get_head_position()
        )
        
        if angle_offset < self.PRE_AIM_ANGLE_THRESHOLD:
            return 1.0 - (angle_offset / self.PRE_AIM_ANGLE_THRESHOLD)
        return 0.0
    
    def score_info(self, peek: PeekEvent, context: WorldState) -> float:
        """Was peek based on information?"""
        recent_sounds = context.get_sounds_in_window(
            peek.tick,
            self.RECENT_SOUND_WINDOW
        )
        
        # Check if player could hear enemy
        for sound in recent_sounds:
            if sound.source_team != peek.player_team:
                if context.can_hear(peek.player_id, sound):
                    return 1.0
        
        # Check if teammate spotted enemy recently
        recent_spots = context.get_recent_spots(peek.tick, 3000)
        if any(s.target_id == peek.target_id for s in recent_spots):
            return 0.8
        
        return 0.0
    
    def score_trade_setup(self, peek: PeekEvent, context: WorldState) -> float:
        """Is a trade available?"""
        teammates = context.get_alive_teammates(peek.player_id)
        
        for tm in teammates:
            dist = tm.position.distance_to(peek.position)
            if dist < self.TRADE_AVAILABLE_DISTANCE:
                # Check if teammate has LOS to peek area
                if context.visibility.can_see(tm.id, peek.target_id):
                    return 1.0
                # Check if teammate could quickly get LOS
                time_to_los = self.estimate_time_to_los(tm, peek.target_position)
                if time_to_los < 1.0:  # 1 second
                    return 0.7
        
        return 0.0
```

### Output Schema

```python
@dataclass
class PeekAnalysis:
    tick: int
    player_id: str
    classification: PeekClassification  # smart, info, forced, ego, panic
    pre_aim_score: float
    info_score: float
    trade_score: float
    outcome: str  # kill, death, damage, none
    risk_reward_ratio: float
```

---

## Module B: Utility Intelligence

### Purpose
Measure effectiveness of every utility throw.

### Analysis Logic

```python
class UtilityAnalyzer:
    def analyze_flash(self, flash: FlashEvent, context: WorldState) -> FlashAnalysis:
        # Get all players affected
        affects = []
        for player in context.get_all_players():
            blind_duration = self.compute_blind_duration(
                flash.position,
                player.position,
                player.view_angles
            )
            if blind_duration > 0:
                affects.append(PlayerBlind(
                    player_id=player.id,
                    duration=blind_duration,
                    is_enemy=player.team != flash.thrower_team,
                    is_self=player.id == flash.thrower_id
                ))
        
        enemies_flashed = [a for a in affects if a.is_enemy]
        team_flashed = [a for a in affects if not a.is_enemy and not a.is_self]
        
        return FlashAnalysis(
            enemies_blinded=len(enemies_flashed),
            team_blinded=len(team_flashed),
            self_flash=any(a.is_self for a in affects),
            avg_enemy_blind_duration=mean([a.duration for a in enemies_flashed]) if enemies_flashed else 0,
            full_blinds=sum(1 for a in enemies_flashed if a.duration > 2.0),
            flash_roi=self.compute_flash_roi(enemies_flashed, team_flashed)
        )
    
    def analyze_smoke(self, smoke: SmokeEvent, context: WorldState) -> SmokeAnalysis:
        # Check what sightlines it blocks
        blocked_sightlines = []
        
        for sightline in context.map.common_sightlines:
            if smoke.blocks_sightline(sightline):
                blocked_sightlines.append(sightline)
        
        # Check timing vs enemy rotations
        timing_score = 0.0
        for enemy in context.get_alive_enemies(smoke.thrower_id):
            time_to_smoke = self.estimate_time_to_position(
                enemy,
                smoke.position
            )
            if 0 < time_to_smoke < 3.0:
                timing_score += 1.0  # Caught enemy rotation
        
        return SmokeAnalysis(
            blocked_sightlines=blocked_sightlines,
            timing_score=timing_score,
            duration=SMOKE_DURATION,
            wasted=len(blocked_sightlines) == 0
        )
    
    def analyze_molly(self, molly: MollyEvent, context: WorldState) -> MollyAnalysis:
        # Calculate area denial
        denial_time = molly.duration
        damage_dealt = 0
        
        for tick in range(molly.start_tick, molly.end_tick):
            for player in context.get_players_at_tick(tick):
                if molly.area.contains(player.position):
                    damage_dealt += MOLLY_DPS * TICK_INTERVAL
        
        return MollyAnalysis(
            denial_time=denial_time,
            area_denied=molly.area.size,
            damage_dealt=damage_dealt,
            enemies_displaced=self.count_displaced_enemies(molly, context),
            roi=self.compute_molly_roi(denial_time, damage_dealt)
        )
```

---

## Module C: Trade Discipline Index

### Purpose
Evaluate trade potential and execution for every death.

```python
class TradeAnalyzer:
    PERFECT_TRADE_WINDOW = 1500   # ms
    LATE_TRADE_WINDOW = 3000      # ms
    MAX_TRADE_DISTANCE = 800      # units
    
    def analyze_trade(self, death: DeathEvent, context: WorldState) -> TradeAnalysis:
        victim = context.get_player(death.victim_id)
        killer = context.get_player(death.attacker_id)
        
        # Find nearest alive teammate at time of death
        teammates = context.get_alive_teammates(death.victim_id, at_tick=death.tick)
        if not teammates:
            return TradeAnalysis(
                possible=False,
                reason='no_teammates_alive'
            )
        
        nearest = min(teammates, key=lambda t: t.position.distance_to(victim.position))
        distance = nearest.position.distance_to(victim.position)
        
        # Check if trade was possible
        if distance > self.MAX_TRADE_DISTANCE:
            return TradeAnalysis(
                possible=False,
                reason='teammate_too_far',
                nearest_distance=distance
            )
        
        # Check if teammate had/could get LOS
        had_los = context.visibility.can_see(nearest.id, killer.id, at_tick=death.tick)
        
        # Look for actual trade
        trade_kill = self.find_trade_kill(death, context)
        
        if trade_kill:
            delay = (trade_kill.tick - death.tick) * TICK_TO_MS
            classification = 'perfect' if delay < self.PERFECT_TRADE_WINDOW else 'late'
        else:
            classification = 'missed'
            delay = None
        
        return TradeAnalysis(
            possible=True,
            happened=trade_kill is not None,
            classification=classification,
            delay_ms=delay,
            nearest_teammate_id=nearest.id,
            nearest_distance=distance,
            teammate_had_los=had_los,
            teammate_was_flashed=nearest.is_flashed,
            teammate_crosshair_on_enemy=self.check_crosshair_on_enemy(nearest, killer)
        )
```

---

## Module D: Crosshair Discipline

### Purpose
Measure aim fundamentals per tick.

```python
class CrosshairDisciplineAnalyzer:
    HEAD_LEVEL_TOLERANCE = 32  # units (roughly head hitbox)
    
    def analyze_round(self, round_data: RoundData, context: WorldState) -> CrosshairAnalysis:
        metrics = {
            'head_level_ticks': 0,
            'total_tracked_ticks': 0,
            'pre_aim_correct': 0,
            'flick_count': 0,
            'total_kills': 0,
        }
        
        for tick in round_data.ticks:
            player = context.get_player_at_tick(round_data.player_id, tick)
            
            if not player.is_alive:
                continue
            
            # Check head-level tracking
            nearest_enemy = self.get_nearest_visible_enemy(player, context, tick)
            if nearest_enemy:
                crosshair_height = self.compute_crosshair_height_at_point(
                    player.position,
                    player.view_angles,
                    nearest_enemy.position
                )
                head_height = nearest_enemy.position.z + STANDING_HEAD_OFFSET
                
                if abs(crosshair_height - head_height) < self.HEAD_LEVEL_TOLERANCE:
                    metrics['head_level_ticks'] += 1
                
                metrics['total_tracked_ticks'] += 1
        
        # Analyze kills for flick dependency
        for kill in round_data.kills:
            view_delta = self.compute_view_delta_before_kill(kill, context)
            if view_delta > 30:  # Large angle correction
                metrics['flick_count'] += 1
            else:
                metrics['pre_aim_correct'] += 1
            metrics['total_kills'] += 1
        
        return CrosshairAnalysis(
            head_level_pct=metrics['head_level_ticks'] / max(metrics['total_tracked_ticks'], 1),
            pre_aim_pct=metrics['pre_aim_correct'] / max(metrics['total_kills'], 1),
            flick_dependency_pct=metrics['flick_count'] / max(metrics['total_kills'], 1),
            discipline_score=self.compute_discipline_score(metrics)
        )
```

---

## Module E: Rotation IQ

### Purpose
Measure information processing and rotation decisions.

```python
class RotationAnalyzer:
    def analyze_rotation(self, rotation: RotationEvent, context: WorldState) -> RotationAnalysis:
        # When did info become available?
        info_tick = self.find_info_availability_tick(rotation, context)
        
        # When did player start rotating?
        reaction_time = (rotation.start_tick - info_tick) * TICK_TO_MS
        
        # Was rotation correct?
        actual_site = context.get_actual_attack_site(rotation.round_id)
        rotated_to_correct = rotation.target_site == actual_site
        
        # Did they over-rotate?
        over_rotation = self.detect_over_rotation(rotation, context)
        
        return RotationAnalysis(
            reaction_time_ms=reaction_time,
            correct_site=rotated_to_correct,
            over_rotated=over_rotation,
            ignored_info=reaction_time > 5000,  # Ignored clear info
            game_sense_score=self.compute_game_sense_score(
                reaction_time, rotated_to_correct, over_rotation
            )
        )
```

---

## Module F: Round Simulator

### Purpose
Model "what-if" scenarios.

```python
class RoundSimulator:
    def simulate_alternate(self, round_data: RoundData, change: ScenarioChange) -> SimulationResult:
        # Clone round state
        sim_state = round_data.clone()
        
        # Apply change
        if change.type == 'delayed_peek':
            # Replay round with peek delayed
            for event in sim_state.events:
                if event.id == change.event_id:
                    event.tick += change.delay_ticks
            
            # Recalculate outcomes
            new_outcomes = self.replay_round(sim_state)
            
        elif change.type == 'alternate_rotation':
            # Model different rotation timing
            pass
        
        # Compute win probability
        original_prob = self.compute_win_probability(round_data)
        new_prob = self.compute_win_probability(new_outcomes)
        
        return SimulationResult(
            original_win_prob=original_prob,
            simulated_win_prob=new_prob,
            delta=new_prob - original_prob,
            key_changes=self.identify_key_changes(round_data, new_outcomes)
        )
```

---

## Module G: Tilt Detector

### Purpose
Detect mental state degradation.

```python
class TiltDetector:
    def analyze_match(self, match_data: MatchData) -> TiltAnalysis:
        indicators = []
        
        for round_num, round_data in enumerate(match_data.rounds):
            player = round_data.get_player(match_data.target_player)
            
            # Solo push detection
            solo_pushes = self.count_solo_pushes(player, round_data)
            
            # Position consistency
            position_variance = self.compute_position_variance(player, round_data)
            
            # Spray pattern quality
            spray_accuracy = self.analyze_spray_patterns(player, round_data)
            
            indicators.append(RoundIndicators(
                round=round_num,
                solo_pushes=solo_pushes,
                position_variance=position_variance,
                spray_accuracy=spray_accuracy
            ))
        
        # Detect tilt onset
        tilt_start = self.find_tilt_onset(indicators)
        severity = self.compute_tilt_severity(indicators, tilt_start)
        
        return TiltAnalysis(
            tilt_detected=tilt_start is not None,
            tilt_start_round=tilt_start,
            severity_pct=severity,
            indicators=indicators
        )
```

---

## Module H: Soft-Cheat Pattern Detection

### Purpose
Detect suspicious patterns (not accusations).

```python
class CheatPatternDetector:
    def analyze_player(self, player_data: PlayerMatchData) -> SuspicionAnalysis:
        patterns = []
        
        # Wall pre-aim detection
        wall_preaims = self.detect_wall_preaims(player_data)
        if wall_preaims:
            patterns.append(SuspicionPattern(
                type='wall_preaim',
                occurrences=len(wall_preaims),
                confidence=self.compute_preaim_confidence(wall_preaims)
            ))
        
        # Reaction time clustering
        reaction_times = self.extract_reaction_times(player_data)
        if self.has_inhuman_clusters(reaction_times):
            patterns.append(SuspicionPattern(
                type='reaction_cluster',
                occurrences=len(reaction_times),
                confidence=self.compute_reaction_confidence(reaction_times)
            ))
        
        # Smoke tracking
        smoke_tracks = self.detect_smoke_tracking(player_data)
        if smoke_tracks:
            patterns.append(SuspicionPattern(
                type='smoke_tracking',
                occurrences=len(smoke_tracks),
                confidence=self.compute_tracking_confidence(smoke_tracks)
            ))
        
        # Aggregate
        overall_suspicion = self.aggregate_suspicion(patterns)
        
        return SuspicionAnalysis(
            patterns=patterns,
            overall_probability=overall_suspicion,
            is_accusation=False,  # Always explicit
            disclaimer="Statistical analysis only. Not a definitive cheat detection."
        )
```

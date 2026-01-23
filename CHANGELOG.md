# Changelog

All notable changes to Sacrilege Engine will be documented in this file.

## [Unreleased]

## [1.4.1] - 2026-01-23

### Added  
- **Timeline kill markers** - CT (blue) and T (orange) death dots on timeline
- **Round numbers** on timeline every 3rd round
- **Enhanced player cards** - Grade badges, selection glow, colored K/D

### Fixed
- Round kills now recalculate correctly when seeking
- Player card selection highlight

## [1.4.0] - 2026-01-20

### Added
- **M key** - Heatmap overlay showing death positions
- **B key** - Bookmark current position for later review
- **J key** - Export analysis to JSON file
- **config.json** - User preferences file
- **Player card click** - Select player by clicking their card
- **Death position tracking** - For heatmap visualization
- **Integration tests** - 6 new tests for demo parsing pipeline

### Changed
- Enhanced _handle_click for player card detection
- Heatmap renders CT (blue) and T (orange) deaths with glow
- Timeline is now clickable for seeking

## [1.3.0] - 2026-01-20

### Added
- **Premium UI Theme** with glassmorphism-inspired design
- **60+ color definitions** including neon CT/T colors and grade-specific colors
- **F12 Screenshot** capture (saves to ~/Downloads)
- **H key** for help overlay toggle
- **F key** for fullscreen toggle
- **Unit Tests** for DeathAnalyzer (15 test cases, 100% pass)
- **UI Helper Functions** for glow effects and rounded rectangles

### Changed
- Upgraded color scheme with vibrant neon accents
- Improved controls hint bar with all keybindings
- Grade colors now distinct: S=Gold, A=Green, B=Blue, C=Silver, D=Orange, F=Red

### Fixed
- Color overflow bug in animated logo (value exceeded 255)
- Removed deprecated MCP integration

### Removed
- MCP server (src/mcp_server.py) - focusing on core functionality

## [1.2.0] - 2026-01-17

### Added
- **BRUTAL Death Analyzer** with 15 mistake classifications
- **Blame Score System** (0-100%) for death accountability
- **Live Player Rankings** with S/A/B/C/D/F grades
- **Performance Scoring** based on K/D and tactical mistakes
- **Trade Detection** for deaths
- **Death Analysis Popups** on radar during playback
- **Rankings Panel** in radar replayer UI

### Changed
- Enhanced radar UI with larger fonts throughout
- Improved legend visibility
- Better statistics panel layout

### Fixed
- Player position tracking at time of death
- Kill/death counting for rankings
- Round reset for death analysis

## [1.1.0] - 2026-01-16

### Added
- Native Python radar replayer with pygame
- Live statistics panel (HP, equipment, kills)
- Active utility counter (smokes, fires)
- Map overlay support for all competitive maps
- Player card enhancements (K/D, weapon, defuser)
- Kill animations on radar
- Bomb carrier indicator

### Changed
- Removed legacy HTML radar implementation
- Enhanced scoreboard with alive indicators

## [1.0.0] - 2026-01-16

### Added
- Initial release
- Demo parsing with demoparser2
- 8 intelligence modules
- Heatmap generation
- GitHub repository setup
- IEEE technical paper

---

## Version Format

`MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes

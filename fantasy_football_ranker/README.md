# Fantasy Football Ranker

A comprehensive Python-based fantasy football ranking system with automated data scraping and advanced ranking algorithms.

## Features

### Data Scraping
- **Pro Football Reference**: Player statistics, snap counts, red zone usage
- **ESPN**: Weekly projections, injury reports, depth charts
- **Vegas Lines**: Point spreads, over/unders, implied team totals

### Ranking Algorithm (Coming Soon)
- VORP (Value Over Replacement Player)
- Bayesian updating (preseason priors + in-season performance)
- Opportunity metrics (target share, snap counts, red zone usage)
- Situational adjustments (strength of schedule, game script)
- Risk assessment (injury history, volatility)

### League Format Support
- Standard scoring
- Half-PPR
- Full PPR
- Superflex

## Installation

```bash
cd fantasy_football_ranker
pip install -r requirements.txt
```

## Usage

### Scrape Data
```bash
# Scrape current week
python main.py scrape

# Scrape specific week
python main.py scrape --season 2024 --week 5
```

### Generate Rankings (Coming Soon)
```bash
python main.py rank --format ppr
```

### Export Output (Coming Soon)
```bash
python main.py output --type csv
python main.py output --type html
```

## Project Structure

```
fantasy_football_ranker/
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuration and league settings
├── scrapers/
│   ├── __init__.py
│   ├── base.py              # Base scraper class
│   ├── pro_football_reference.py
│   ├── espn.py
│   ├── vegas.py
│   └── orchestrator.py      # Scraper coordination
├── database/
│   ├── __init__.py
│   └── models.py            # SQLAlchemy models
├── ranking/
│   └── __init__.py          # Ranking algorithms (coming soon)
├── output/
│   └── __init__.py          # Output generation (coming soon)
├── utils/
│   ├── __init__.py
│   └── helpers.py           # Utility functions
├── main.py                  # CLI entry point
├── requirements.txt
└── README.md
```

## Database Schema

The system uses SQLite with the following tables:
- `players` - Core player information
- `player_stats` - Season-level statistics
- `weekly_stats` - Game-by-game statistics
- `projections` - Fantasy projections from various sources
- `injuries` - Injury reports and status
- `game_odds` - Vegas lines and game environment
- `rankings` - Calculated player rankings

## Configuration

League settings can be customized in `config/settings.py` or by using preset formats:
- `standard` - No PPR
- `half_ppr` - 0.5 points per reception
- `full_ppr` - 1.0 points per reception
- `superflex` - Full PPR with QB-eligible flex

## License

MIT License

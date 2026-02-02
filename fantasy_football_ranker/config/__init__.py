"""Configuration module for Fantasy Football Ranker."""
from .settings import (
    LeagueSettings,
    ScraperConfig,
    RankingConfig,
    DEFAULT_LEAGUE,
    DEFAULT_SCRAPER,
    DEFAULT_RANKING,
    LEAGUE_PRESETS,
    load_league_config,
    save_league_config,
    BASE_DIR,
    DATA_DIR,
    OUTPUT_DIR,
    DB_PATH,
)

__all__ = [
    "LeagueSettings",
    "ScraperConfig",
    "RankingConfig",
    "DEFAULT_LEAGUE",
    "DEFAULT_SCRAPER",
    "DEFAULT_RANKING",
    "LEAGUE_PRESETS",
    "load_league_config",
    "save_league_config",
    "BASE_DIR",
    "DATA_DIR",
    "OUTPUT_DIR",
    "DB_PATH",
]

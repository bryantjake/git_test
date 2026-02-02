"""Scraper modules for Fantasy Football Ranker."""
from .base import BaseScraper
from .pro_football_reference import (
    ProFootballReferenceScraper,
    PlayerStats,
    GameLog,
)
from .espn import (
    ESPNScraper,
    ESPNProjection,
    InjuryReport,
)
from .vegas import (
    VegasScraper,
    GameLines,
    calculate_schedule_difficulty,
)
from .orchestrator import (
    ScraperOrchestrator,
    run_daily_update,
)

__all__ = [
    "BaseScraper",
    "ProFootballReferenceScraper",
    "PlayerStats",
    "GameLog",
    "ESPNScraper",
    "ESPNProjection",
    "InjuryReport",
    "VegasScraper",
    "GameLines",
    "calculate_schedule_difficulty",
    "ScraperOrchestrator",
    "run_daily_update",
]

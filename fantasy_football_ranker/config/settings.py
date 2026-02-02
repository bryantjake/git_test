"""
Fantasy Football Ranker Configuration Settings
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import json

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
DB_PATH = DATA_DIR / "fantasy_football.db"


@dataclass
class LeagueSettings:
    """Configurable league format settings."""
    name: str = "default"
    ppr_value: float = 1.0  # 0 for standard, 0.5 for half-PPR, 1.0 for full PPR
    roster_size: int = 15
    starting_qb: int = 1
    starting_rb: int = 2
    starting_wr: int = 2
    starting_te: int = 1
    starting_flex: int = 1
    starting_dst: int = 1
    starting_k: int = 1
    bench_spots: int = 6

    # Scoring settings
    passing_td: float = 4.0
    passing_yard: float = 0.04
    passing_int: float = -2.0
    rushing_td: float = 6.0
    rushing_yard: float = 0.1
    receiving_td: float = 6.0
    receiving_yard: float = 0.1
    reception: float = 1.0  # This is the PPR value
    fumble_lost: float = -2.0
    two_pt_conversion: float = 2.0

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "ppr_value": self.ppr_value,
            "roster_size": self.roster_size,
            "scoring": {
                "passing_td": self.passing_td,
                "passing_yard": self.passing_yard,
                "passing_int": self.passing_int,
                "rushing_td": self.rushing_td,
                "rushing_yard": self.rushing_yard,
                "receiving_td": self.receiving_td,
                "receiving_yard": self.receiving_yard,
                "reception": self.reception,
                "fumble_lost": self.fumble_lost,
                "two_pt_conversion": self.two_pt_conversion,
            }
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "LeagueSettings":
        scoring = data.get("scoring", {})
        return cls(
            name=data.get("name", "default"),
            ppr_value=data.get("ppr_value", 1.0),
            roster_size=data.get("roster_size", 15),
            passing_td=scoring.get("passing_td", 4.0),
            passing_yard=scoring.get("passing_yard", 0.04),
            passing_int=scoring.get("passing_int", -2.0),
            rushing_td=scoring.get("rushing_td", 6.0),
            rushing_yard=scoring.get("rushing_yard", 0.1),
            receiving_td=scoring.get("receiving_td", 6.0),
            receiving_yard=scoring.get("receiving_yard", 0.1),
            reception=scoring.get("reception", 1.0),
            fumble_lost=scoring.get("fumble_lost", -2.0),
            two_pt_conversion=scoring.get("two_pt_conversion", 2.0),
        )


@dataclass
class ScraperConfig:
    """Configuration for web scrapers."""
    # Request settings
    request_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 2.0

    # Rate limiting (seconds between requests)
    rate_limit_pfr: float = 3.0  # Pro Football Reference is strict
    rate_limit_espn: float = 1.0
    rate_limit_vegas: float = 1.5

    # User agent rotation
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ])

    # Data source URLs
    pfr_base_url: str = "https://www.pro-football-reference.com"
    espn_base_url: str = "https://www.espn.com/nfl"
    espn_api_base: str = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"


@dataclass
class RankingConfig:
    """Configuration for ranking algorithm."""
    # VORP baseline percentiles by position
    replacement_level: Dict[str, float] = field(default_factory=lambda: {
        "QB": 0.67,   # Top 12 QBs are starters
        "RB": 0.75,   # Top 24 RBs
        "WR": 0.80,   # Top 30 WRs
        "TE": 0.67,   # Top 12 TEs
        "K": 0.60,
        "DST": 0.60,
    })

    # Bayesian prior weights (0-1, higher = more weight on priors)
    prior_weight_early_season: float = 0.7  # Weeks 1-4
    prior_weight_mid_season: float = 0.4    # Weeks 5-10
    prior_weight_late_season: float = 0.2   # Weeks 11+

    # Feature weights for ranking
    weights: Dict[str, float] = field(default_factory=lambda: {
        "vorp": 0.30,
        "opportunity": 0.25,
        "efficiency": 0.20,
        "schedule": 0.10,
        "consistency": 0.10,
        "risk": 0.05,
    })


# Default configurations
DEFAULT_LEAGUE = LeagueSettings()
DEFAULT_SCRAPER = ScraperConfig()
DEFAULT_RANKING = RankingConfig()

# Predefined league formats
LEAGUE_PRESETS = {
    "standard": LeagueSettings(name="standard", ppr_value=0.0, reception=0.0),
    "half_ppr": LeagueSettings(name="half_ppr", ppr_value=0.5, reception=0.5),
    "full_ppr": LeagueSettings(name="full_ppr", ppr_value=1.0, reception=1.0),
    "superflex": LeagueSettings(
        name="superflex",
        ppr_value=1.0,
        reception=1.0,
        starting_qb=1,
        starting_flex=2,  # One can be a QB
    ),
}


def load_league_config(config_path: Optional[Path] = None) -> LeagueSettings:
    """Load league configuration from JSON file or return default."""
    if config_path and config_path.exists():
        with open(config_path) as f:
            return LeagueSettings.from_dict(json.load(f))
    return DEFAULT_LEAGUE


def save_league_config(settings: LeagueSettings, config_path: Path) -> None:
    """Save league configuration to JSON file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(settings.to_dict(), f, indent=2)

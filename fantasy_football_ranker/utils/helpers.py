"""
Utility helper functions for Fantasy Football Ranker.
"""
import re
from datetime import datetime, date
from typing import Optional
from dateutil import parser as date_parser


def normalize_player_name(name: str) -> str:
    """
    Normalize player names for consistent matching across data sources.

    Handles:
    - Suffixes (Jr., Sr., III, etc.)
    - Punctuation differences
    - Case normalization
    - Common abbreviation differences
    """
    if not name:
        return ""

    # Convert to lowercase and strip whitespace
    normalized = name.lower().strip()

    # Remove common suffixes for matching purposes
    suffixes = [" jr.", " jr", " sr.", " sr", " iii", " ii", " iv", " v"]
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]

    # Remove punctuation except spaces and hyphens
    normalized = re.sub(r"[^\w\s\-]", "", normalized)

    # Normalize multiple spaces to single space
    normalized = re.sub(r"\s+", " ", normalized)

    # Handle common name variations
    name_mappings = {
        "patrick mahomes": "patrick mahomes",
        "pat mahomes": "patrick mahomes",
        "mike williams": "michael williams",
        "mike evans": "michael evans",
        "gabe davis": "gabriel davis",
        "dj moore": "d.j. moore",
        "aj brown": "a.j. brown",
        "cj stroud": "c.j. stroud",
        "tj hockenson": "t.j. hockenson",
    }

    return name_mappings.get(normalized, normalized)


def parse_nfl_date(date_str: str) -> Optional[date]:
    """
    Parse various date formats commonly found in NFL data sources.

    Returns:
        date object or None if parsing fails
    """
    if not date_str:
        return None

    try:
        # Try common formats first
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y%m%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        # Fall back to dateutil parser
        return date_parser.parse(date_str).date()
    except (ValueError, TypeError):
        return None


def get_current_nfl_season() -> int:
    """
    Get the current NFL season year.

    NFL season is determined by:
    - If current month is before March, it's the previous year's season
    - Otherwise, it's the current year's season
    """
    today = date.today()
    if today.month < 3:
        return today.year - 1
    return today.year


def get_current_nfl_week(season: Optional[int] = None) -> int:
    """
    Estimate the current NFL week based on date.

    NFL regular season typically starts the Thursday after Labor Day.
    This is an approximation and should be updated with actual schedule data.

    Args:
        season: NFL season year (defaults to current season)

    Returns:
        Current week number (1-18 for regular season, 0 for preseason, 19+ for playoffs)
    """
    if season is None:
        season = get_current_nfl_season()

    today = date.today()

    # Approximate season start (first Thursday after first Monday in September)
    # This is a simplification - real implementation should use actual schedule
    september_first = date(season, 9, 1)

    # Find first Monday in September
    days_until_monday = (7 - september_first.weekday()) % 7
    if september_first.weekday() == 0:  # Already Monday
        first_monday = september_first
    else:
        first_monday = september_first + __import__("datetime").timedelta(days=days_until_monday)

    # Season starts Thursday after Labor Day (first Monday in September)
    season_start = first_monday + __import__("datetime").timedelta(days=3)

    if today < season_start:
        return 0  # Preseason

    # Calculate weeks since season start
    days_since_start = (today - season_start).days
    current_week = (days_since_start // 7) + 1

    # Cap at 18 for regular season
    return min(current_week, 18)


def calculate_fantasy_points(
    stats: dict,
    ppr_value: float = 1.0,
    passing_td: float = 4.0,
    passing_yard: float = 0.04,
    passing_int: float = -2.0,
    rushing_td: float = 6.0,
    rushing_yard: float = 0.1,
    receiving_td: float = 6.0,
    receiving_yard: float = 0.1,
    fumble_lost: float = -2.0,
    two_pt: float = 2.0,
) -> float:
    """
    Calculate fantasy points from a stats dictionary.

    Args:
        stats: Dictionary containing player statistics
        ppr_value: Points per reception
        Other args: Scoring settings

    Returns:
        Total fantasy points
    """
    points = 0.0

    # Passing
    points += stats.get("passing_yards", 0) * passing_yard
    points += stats.get("passing_tds", 0) * passing_td
    points += stats.get("interceptions", 0) * passing_int

    # Rushing
    points += stats.get("rushing_yards", 0) * rushing_yard
    points += stats.get("rushing_tds", 0) * rushing_td

    # Receiving
    points += stats.get("receiving_yards", 0) * receiving_yard
    points += stats.get("receiving_tds", 0) * receiving_td
    points += stats.get("receptions", 0) * ppr_value

    # Misc
    points += stats.get("fumbles_lost", 0) * fumble_lost
    points += stats.get("two_pt_conversions", 0) * two_pt

    return points


def clean_numeric(value: str) -> Optional[float]:
    """
    Clean and convert a string value to float.

    Handles:
    - Commas in numbers
    - Percentages
    - Empty strings
    - Invalid values
    """
    if not value or value in ("", "-", "--", "N/A", "n/a"):
        return None

    try:
        # Remove commas and whitespace
        cleaned = str(value).replace(",", "").replace(" ", "")

        # Handle percentages
        if cleaned.endswith("%"):
            return float(cleaned[:-1]) / 100

        return float(cleaned)
    except (ValueError, TypeError):
        return None


def team_abbr_mapping() -> dict:
    """
    Return a mapping of team abbreviations to standardized format.
    Different sources use different abbreviations.
    """
    return {
        # Standard -> Standard (identity mappings)
        "ARI": "ARI", "ATL": "ATL", "BAL": "BAL", "BUF": "BUF",
        "CAR": "CAR", "CHI": "CHI", "CIN": "CIN", "CLE": "CLE",
        "DAL": "DAL", "DEN": "DEN", "DET": "DET", "GB": "GB",
        "HOU": "HOU", "IND": "IND", "JAX": "JAX", "KC": "KC",
        "LAC": "LAC", "LAR": "LAR", "LV": "LV", "MIA": "MIA",
        "MIN": "MIN", "NE": "NE", "NO": "NO", "NYG": "NYG",
        "NYJ": "NYJ", "PHI": "PHI", "PIT": "PIT", "SEA": "SEA",
        "SF": "SF", "TB": "TB", "TEN": "TEN", "WAS": "WAS",
        # Alternate abbreviations
        "GNB": "GB", "GBP": "GB",
        "KAN": "KC", "KCC": "KC",
        "LVR": "LV", "OAK": "LV", "RAI": "LV",
        "LAX": "LAR", "RAM": "LAR", "STL": "LAR",
        "SDG": "LAC", "SD": "LAC",
        "NOR": "NO", "NOS": "NO",
        "SFO": "SF", "SAN": "SF",
        "TAM": "TB", "TBB": "TB",
        "WFT": "WAS", "WSH": "WAS",
        "JAC": "JAX",
        "NEP": "NE", "NWE": "NE",
        "PHO": "ARI",
    }


def normalize_team(team: str) -> str:
    """Normalize team abbreviation to standard format."""
    if not team:
        return ""
    mapping = team_abbr_mapping()
    return mapping.get(team.upper().strip(), team.upper().strip())

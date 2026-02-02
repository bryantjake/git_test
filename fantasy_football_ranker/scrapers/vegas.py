"""
Vegas lines scraper for game environment data.

Scrapes:
- Point spreads
- Over/under totals
- Implied team totals
- Moneylines
"""
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from .base import BaseScraper
from config.settings import ScraperConfig
from utils.helpers import normalize_team, clean_numeric


@dataclass
class GameLines:
    """Container for Vegas betting lines for a single game."""
    game_id: str
    season: int
    week: int
    game_date: str
    home_team: str
    away_team: str

    # Spread (positive = home underdog)
    spread: float = 0.0
    spread_home_odds: int = -110
    spread_away_odds: int = -110

    # Over/Under total
    over_under: float = 0.0
    over_odds: int = -110
    under_odds: int = -110

    # Implied team totals (derived from spread + O/U)
    home_implied_total: float = 0.0
    away_implied_total: float = 0.0

    # Moneyline
    home_moneyline: int = 0
    away_moneyline: int = 0

    # Win probability (implied from moneyline)
    home_win_probability: float = 0.5
    away_win_probability: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def calculate_implied_totals(self) -> None:
        """Calculate implied team totals from spread and O/U."""
        if self.over_under > 0 and self.spread != 0:
            # Implied total = (O/U + spread) / 2 for favorite
            # Implied total = (O/U - spread) / 2 for underdog
            self.home_implied_total = (self.over_under - self.spread) / 2
            self.away_implied_total = (self.over_under + self.spread) / 2
        elif self.over_under > 0:
            self.home_implied_total = self.over_under / 2
            self.away_implied_total = self.over_under / 2


class VegasScraper(BaseScraper):
    """
    Scraper for Vegas betting lines.

    Scrapes publicly available odds data for game environment analysis.
    """

    # ESPN API endpoint for scoreboard (includes odds)
    ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config)
        self.rate_limit_delay = self.config.rate_limit_vegas

    def get_data_source_name(self) -> str:
        return "Vegas Lines"

    def scrape(
        self,
        season: int,
        week: Optional[int] = None,
    ) -> List[GameLines]:
        """
        Scrape Vegas lines for games.

        Args:
            season: NFL season year
            week: Specific week (None for current)

        Returns:
            List of GameLines objects
        """
        self.logger.info(f"Scraping Vegas lines for {season} season, week {week}")

        # Try ESPN API first (most reliable for public odds)
        games = self._scrape_espn_odds(season, week)

        if not games:
            self.logger.warning("No games found, trying alternative source")
            games = self._scrape_odds_web(season, week)

        return games

    def _scrape_espn_odds(
        self,
        season: int,
        week: Optional[int] = None,
    ) -> List[GameLines]:
        """
        Scrape odds from ESPN API scoreboard endpoint.

        Args:
            season: NFL season year
            week: Week number

        Returns:
            List of GameLines objects
        """
        games = []

        params = {
            "dates": season,
        }
        if week:
            params["week"] = week

        try:
            response = self._fetch_page(
                self.ESPN_SCOREBOARD_URL,
                "espn_odds",
                self.rate_limit_delay,
                params=params,
            )
            data = response.json()

            events = data.get("events", [])

            for event in events:
                game_id = event.get("id", "")
                competitions = event.get("competitions", [{}])
                if not competitions:
                    continue

                competition = competitions[0]

                # Parse teams
                competitors = competition.get("competitors", [])
                if len(competitors) < 2:
                    continue

                home_team = ""
                away_team = ""

                for team in competitors:
                    team_info = team.get("team", {})
                    team_abbr = team_info.get("abbreviation", "")

                    if team.get("homeAway") == "home":
                        home_team = normalize_team(team_abbr)
                    else:
                        away_team = normalize_team(team_abbr)

                # Parse odds
                odds_info = competition.get("odds", [{}])
                if not odds_info:
                    odds_data = {}
                else:
                    odds_data = odds_info[0] if isinstance(odds_info, list) else odds_info

                # Extract spread and over/under
                spread = self._parse_spread(odds_data)
                over_under = clean_numeric(odds_data.get("overUnder")) or 0.0

                # Parse moneylines
                home_ml, away_ml = self._parse_moneylines(odds_data, home_team)

                # Parse game date
                game_date = event.get("date", "")

                game = GameLines(
                    game_id=game_id,
                    season=season,
                    week=week or 0,
                    game_date=game_date,
                    home_team=home_team,
                    away_team=away_team,
                    spread=spread,
                    over_under=over_under,
                    home_moneyline=home_ml,
                    away_moneyline=away_ml,
                    home_win_probability=self._moneyline_to_probability(home_ml),
                    away_win_probability=self._moneyline_to_probability(away_ml),
                )

                game.calculate_implied_totals()
                games.append(game)

            self.logger.info(f"Scraped odds for {len(games)} games")

        except Exception as e:
            self.logger.error(f"Error scraping ESPN odds: {e}")

        return games

    def _scrape_odds_web(
        self,
        season: int,
        week: Optional[int] = None,
    ) -> List[GameLines]:
        """
        Fallback web scraping for odds from ESPN website.

        Args:
            season: NFL season year
            week: Week number

        Returns:
            List of GameLines objects
        """
        games = []

        url = "https://www.espn.com/nfl/schedule"
        params = {}
        if week:
            params["week"] = week

        try:
            response = self._fetch_page(url, "espn_schedule", self.rate_limit_delay, params=params)
            soup = self._parse_html(response.text)

            # Find game cards/rows
            game_sections = soup.find_all("div", class_="ScheduleTables")

            for section in game_sections:
                rows = section.find_all("tr", class_="Table__TR")

                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) < 3:
                        continue

                    # Parse team names
                    team_cells = row.find_all("a", class_="AnchorLink")
                    teams = []

                    for team_link in team_cells:
                        href = team_link.get("href", "")
                        if "/team/" in href:
                            team_match = re.search(r"/team/_/name/(\w+)/", href)
                            if team_match:
                                teams.append(normalize_team(team_match.group(1)))

                    if len(teams) >= 2:
                        away_team = teams[0]
                        home_team = teams[1]

                        # Find odds cell if present
                        odds_cell = row.find("td", class_="odds")
                        spread = 0.0
                        over_under = 0.0

                        if odds_cell:
                            odds_text = self._safe_get_text(odds_cell)
                            spread_match = re.search(r"([+-]?\d+\.?\d*)", odds_text)
                            ou_match = re.search(r"O/U\s*(\d+\.?\d*)", odds_text)

                            if spread_match:
                                spread = float(spread_match.group(1))
                            if ou_match:
                                over_under = float(ou_match.group(1))

                        game = GameLines(
                            game_id=f"{season}_{week}_{away_team}_{home_team}",
                            season=season,
                            week=week or 0,
                            game_date="",
                            home_team=home_team,
                            away_team=away_team,
                            spread=spread,
                            over_under=over_under,
                        )

                        game.calculate_implied_totals()
                        games.append(game)

        except Exception as e:
            self.logger.error(f"Error scraping schedule page for odds: {e}")

        return games

    def _parse_spread(self, odds_data: Dict[str, Any]) -> float:
        """
        Parse spread from odds data.

        Args:
            odds_data: Odds dictionary from API

        Returns:
            Spread value (positive = home underdog)
        """
        # Try direct spread field
        if "spread" in odds_data:
            return clean_numeric(odds_data["spread"]) or 0.0

        # Try details field
        details = odds_data.get("details", "")
        if details:
            # Format: "TEAM -X.X" or "TEAM +X.X"
            spread_match = re.search(r"([+-]\d+\.?\d*)", details)
            if spread_match:
                return float(spread_match.group(1))

        return 0.0

    def _parse_moneylines(
        self,
        odds_data: Dict[str, Any],
        home_team: str,
    ) -> tuple:
        """
        Parse moneylines from odds data.

        Args:
            odds_data: Odds dictionary from API
            home_team: Home team abbreviation

        Returns:
            Tuple of (home_moneyline, away_moneyline)
        """
        home_ml = 0
        away_ml = 0

        # Check for awayTeamOdds and homeTeamOdds
        home_odds = odds_data.get("homeTeamOdds", {})
        away_odds = odds_data.get("awayTeamOdds", {})

        if home_odds and away_odds:
            home_ml = int(clean_numeric(home_odds.get("moneyLine")) or 0)
            away_ml = int(clean_numeric(away_odds.get("moneyLine")) or 0)

        return home_ml, away_ml

    def _moneyline_to_probability(self, moneyline: int) -> float:
        """
        Convert American moneyline to implied probability.

        Args:
            moneyline: American format moneyline

        Returns:
            Implied probability (0-1)
        """
        if moneyline == 0:
            return 0.5

        if moneyline > 0:
            # Underdog: probability = 100 / (moneyline + 100)
            return 100 / (moneyline + 100)
        else:
            # Favorite: probability = |moneyline| / (|moneyline| + 100)
            return abs(moneyline) / (abs(moneyline) + 100)

    def get_game_environment(
        self,
        team: str,
        games: List[GameLines],
    ) -> Optional[Dict[str, Any]]:
        """
        Get game environment metrics for a specific team.

        Args:
            team: Team abbreviation
            games: List of GameLines for the week

        Returns:
            Dictionary with game environment metrics or None
        """
        team = normalize_team(team)

        for game in games:
            if game.home_team == team:
                return {
                    "is_home": True,
                    "opponent": game.away_team,
                    "spread": -game.spread,  # From team's perspective
                    "over_under": game.over_under,
                    "implied_total": game.home_implied_total,
                    "win_probability": game.home_win_probability,
                    "expected_game_script": self._analyze_game_script(
                        game.spread, is_favorite=game.spread < 0
                    ),
                }
            elif game.away_team == team:
                return {
                    "is_home": False,
                    "opponent": game.home_team,
                    "spread": game.spread,  # From team's perspective
                    "over_under": game.over_under,
                    "implied_total": game.away_implied_total,
                    "win_probability": game.away_win_probability,
                    "expected_game_script": self._analyze_game_script(
                        game.spread, is_favorite=game.spread > 0
                    ),
                }

        return None

    def _analyze_game_script(
        self,
        spread: float,
        is_favorite: bool,
    ) -> str:
        """
        Analyze expected game script based on spread.

        Args:
            spread: Point spread
            is_favorite: Whether the team is favored

        Returns:
            Game script description
        """
        abs_spread = abs(spread)

        if abs_spread < 3:
            return "neutral"  # Close game expected
        elif abs_spread < 7:
            if is_favorite:
                return "slight_positive"  # Slight lead expected
            return "slight_negative"  # Slight deficit expected
        elif abs_spread < 10:
            if is_favorite:
                return "positive"  # Lead expected, may run more
            return "negative"  # Trailing, may pass more
        else:
            if is_favorite:
                return "blowout_positive"  # Big lead, garbage time
            return "blowout_negative"  # Playing catch-up


def calculate_schedule_difficulty(
    team: str,
    remaining_games: List[GameLines],
) -> Dict[str, float]:
    """
    Calculate remaining schedule difficulty for a team.

    Args:
        team: Team abbreviation
        remaining_games: List of upcoming games

    Returns:
        Schedule difficulty metrics
    """
    team = normalize_team(team)

    opponent_spreads = []
    total_implied_points = 0
    home_games = 0
    away_games = 0

    for game in remaining_games:
        if game.home_team == team:
            opponent_spreads.append(-game.spread)  # Negative = easier
            total_implied_points += game.home_implied_total
            home_games += 1
        elif game.away_team == team:
            opponent_spreads.append(game.spread)
            total_implied_points += game.away_implied_total
            away_games += 1

    num_games = len(opponent_spreads)

    if num_games == 0:
        return {
            "avg_spread": 0.0,
            "avg_implied_points": 0.0,
            "home_games": 0,
            "away_games": 0,
            "difficulty_rating": 0.5,
        }

    avg_spread = sum(opponent_spreads) / num_games
    avg_implied = total_implied_points / num_games

    # Calculate difficulty rating (0-1 scale)
    # Negative avg_spread = easier, positive = harder
    # Normalize to 0-1 where 0.5 is average
    difficulty = 0.5 + (avg_spread / 28)  # 14 point swing normalized
    difficulty = max(0.1, min(0.9, difficulty))

    return {
        "avg_spread": avg_spread,
        "avg_implied_points": avg_implied,
        "home_games": home_games,
        "away_games": away_games,
        "difficulty_rating": difficulty,
    }

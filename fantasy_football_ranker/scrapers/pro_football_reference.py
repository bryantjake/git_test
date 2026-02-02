"""
Pro Football Reference scraper for player statistics.

Scrapes:
- Season statistics (passing, rushing, receiving)
- Game-by-game logs
- Snap counts
- Red zone usage
- Target data
"""
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import date

from bs4 import BeautifulSoup, Comment

from .base import BaseScraper
from config.settings import ScraperConfig
from utils.helpers import (
    normalize_player_name,
    normalize_team,
    clean_numeric,
    get_current_nfl_season,
)


@dataclass
class PlayerStats:
    """Container for player statistics."""
    player_id: str
    name: str
    team: str
    position: str
    games_played: int = 0
    games_started: int = 0

    # Passing stats
    passing_attempts: int = 0
    passing_completions: int = 0
    passing_yards: int = 0
    passing_tds: int = 0
    interceptions: int = 0
    sacks: int = 0
    sack_yards: int = 0

    # Rushing stats
    rushing_attempts: int = 0
    rushing_yards: int = 0
    rushing_tds: int = 0
    rushing_fumbles: int = 0

    # Receiving stats
    targets: int = 0
    receptions: int = 0
    receiving_yards: int = 0
    receiving_tds: int = 0
    receiving_fumbles: int = 0

    # Advanced metrics
    snap_count: int = 0
    snap_percentage: float = 0.0
    target_share: float = 0.0
    air_yards: int = 0
    red_zone_targets: int = 0
    red_zone_touches: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GameLog:
    """Container for single game statistics."""
    player_id: str
    season: int
    week: int
    date: str
    opponent: str
    home_away: str
    result: str
    stats: Dict[str, Any]


class ProFootballReferenceScraper(BaseScraper):
    """
    Scraper for Pro Football Reference data.

    PFR is rate-limited strictly, so we use conservative delays.
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config)
        self.base_url = self.config.pfr_base_url
        self.rate_limit_delay = self.config.rate_limit_pfr

    def get_data_source_name(self) -> str:
        return "Pro Football Reference"

    def scrape(self, season: Optional[int] = None) -> Dict[str, List[PlayerStats]]:
        """
        Scrape all player statistics for a season.

        Args:
            season: NFL season year (defaults to current season)

        Returns:
            Dictionary with position keys and lists of PlayerStats
        """
        if season is None:
            season = get_current_nfl_season()

        self.logger.info(f"Scraping PFR data for {season} season")

        results = {
            "passing": self._scrape_passing_stats(season),
            "rushing": self._scrape_rushing_stats(season),
            "receiving": self._scrape_receiving_stats(season),
        }

        return results

    def _scrape_passing_stats(self, season: int) -> List[PlayerStats]:
        """Scrape passing statistics."""
        url = f"{self.base_url}/years/{season}/passing.htm"

        try:
            response = self._fetch_page(url, "pfr", self.rate_limit_delay)
            soup = self._parse_html(response.text)

            # Find the stats table
            table = soup.find("table", {"id": "passing"})
            if not table:
                self.logger.warning("Could not find passing table")
                return []

            return self._parse_stats_table(table, "QB")

        except Exception as e:
            self.logger.error(f"Error scraping passing stats: {e}")
            return []

    def _scrape_rushing_stats(self, season: int) -> List[PlayerStats]:
        """Scrape rushing statistics."""
        url = f"{self.base_url}/years/{season}/rushing.htm"

        try:
            response = self._fetch_page(url, "pfr", self.rate_limit_delay)
            soup = self._parse_html(response.text)

            table = soup.find("table", {"id": "rushing"})
            if not table:
                self.logger.warning("Could not find rushing table")
                return []

            return self._parse_stats_table(table, "RB")

        except Exception as e:
            self.logger.error(f"Error scraping rushing stats: {e}")
            return []

    def _scrape_receiving_stats(self, season: int) -> List[PlayerStats]:
        """Scrape receiving statistics."""
        url = f"{self.base_url}/years/{season}/receiving.htm"

        try:
            response = self._fetch_page(url, "pfr", self.rate_limit_delay)
            soup = self._parse_html(response.text)

            table = soup.find("table", {"id": "receiving"})
            if not table:
                self.logger.warning("Could not find receiving table")
                return []

            return self._parse_stats_table(table, "WR")

        except Exception as e:
            self.logger.error(f"Error scraping receiving stats: {e}")
            return []

    def _parse_stats_table(self, table: Any, default_position: str) -> List[PlayerStats]:
        """
        Parse a PFR stats table into PlayerStats objects.

        Args:
            table: BeautifulSoup table element
            default_position: Default position if not found in data

        Returns:
            List of PlayerStats objects
        """
        players = []
        tbody = table.find("tbody")

        if not tbody:
            return players

        rows = tbody.find_all("tr")

        for row in rows:
            # Skip header rows and separator rows
            if row.get("class") and "thead" in row.get("class", []):
                continue

            # Get player info
            player_cell = row.find("td", {"data-stat": "player"})
            if not player_cell:
                continue

            player_link = player_cell.find("a")
            if not player_link:
                continue

            # Extract player ID from href
            href = player_link.get("href", "")
            player_id_match = re.search(r"/players/\w/(\w+)\.htm", href)
            player_id = player_id_match.group(1) if player_id_match else ""

            name = self._safe_get_text(player_link)
            team = self._safe_get_text(row.find("td", {"data-stat": "team"}))
            position = self._safe_get_text(row.find("td", {"data-stat": "pos"})) or default_position

            # Create player stats object
            stats = PlayerStats(
                player_id=player_id,
                name=name,
                team=normalize_team(team),
                position=position.upper(),
            )

            # Parse common stats
            stats.games_played = int(clean_numeric(
                self._safe_get_text(row.find("td", {"data-stat": "g"}))
            ) or 0)
            stats.games_started = int(clean_numeric(
                self._safe_get_text(row.find("td", {"data-stat": "gs"}))
            ) or 0)

            # Parse passing stats
            stats.passing_completions = int(clean_numeric(
                self._safe_get_text(row.find("td", {"data-stat": "pass_cmp"}))
            ) or 0)
            stats.passing_attempts = int(clean_numeric(
                self._safe_get_text(row.find("td", {"data-stat": "pass_att"}))
            ) or 0)
            stats.passing_yards = int(clean_numeric(
                self._safe_get_text(row.find("td", {"data-stat": "pass_yds"}))
            ) or 0)
            stats.passing_tds = int(clean_numeric(
                self._safe_get_text(row.find("td", {"data-stat": "pass_td"}))
            ) or 0)
            stats.interceptions = int(clean_numeric(
                self._safe_get_text(row.find("td", {"data-stat": "pass_int"}))
            ) or 0)

            # Parse rushing stats
            stats.rushing_attempts = int(clean_numeric(
                self._safe_get_text(row.find("td", {"data-stat": "rush_att"}))
            ) or 0)
            stats.rushing_yards = int(clean_numeric(
                self._safe_get_text(row.find("td", {"data-stat": "rush_yds"}))
            ) or 0)
            stats.rushing_tds = int(clean_numeric(
                self._safe_get_text(row.find("td", {"data-stat": "rush_td"}))
            ) or 0)

            # Parse receiving stats
            stats.targets = int(clean_numeric(
                self._safe_get_text(row.find("td", {"data-stat": "targets"}))
            ) or 0)
            stats.receptions = int(clean_numeric(
                self._safe_get_text(row.find("td", {"data-stat": "rec"}))
            ) or 0)
            stats.receiving_yards = int(clean_numeric(
                self._safe_get_text(row.find("td", {"data-stat": "rec_yds"}))
            ) or 0)
            stats.receiving_tds = int(clean_numeric(
                self._safe_get_text(row.find("td", {"data-stat": "rec_td"}))
            ) or 0)

            # Parse fumbles
            fumbles = int(clean_numeric(
                self._safe_get_text(row.find("td", {"data-stat": "fumbles"}))
            ) or 0)
            fumbles_lost = int(clean_numeric(
                self._safe_get_text(row.find("td", {"data-stat": "fumbles_lost"}))
            ) or 0)

            if default_position in ["QB"]:
                # Assume rushing fumbles for QBs
                stats.rushing_fumbles = fumbles_lost
            elif default_position in ["RB"]:
                stats.rushing_fumbles = fumbles_lost
            else:
                stats.receiving_fumbles = fumbles_lost

            players.append(stats)

        self.logger.info(f"Parsed {len(players)} players from {default_position} table")
        return players

    def scrape_snap_counts(self, season: int) -> Dict[str, Dict[str, Any]]:
        """
        Scrape snap count data for the season.

        Args:
            season: NFL season year

        Returns:
            Dictionary mapping player IDs to snap count data
        """
        url = f"{self.base_url}/years/{season}/fantasy.htm"
        snap_data = {}

        try:
            response = self._fetch_page(url, "pfr", self.rate_limit_delay)
            soup = self._parse_html(response.text)

            # Fantasy table has snap count data
            table = soup.find("table", {"id": "fantasy"})
            if not table:
                # Try to find in comments (PFR sometimes hides tables in comments)
                comments = soup.find_all(string=lambda t: isinstance(t, Comment))
                for comment in comments:
                    if "fantasy" in comment:
                        comment_soup = BeautifulSoup(comment, "lxml")
                        table = comment_soup.find("table", {"id": "fantasy"})
                        if table:
                            break

            if not table:
                self.logger.warning("Could not find fantasy/snap count table")
                return snap_data

            tbody = table.find("tbody")
            if not tbody:
                return snap_data

            for row in tbody.find_all("tr"):
                player_cell = row.find("td", {"data-stat": "player"})
                if not player_cell:
                    continue

                player_link = player_cell.find("a")
                if not player_link:
                    continue

                href = player_link.get("href", "")
                player_id_match = re.search(r"/players/\w/(\w+)\.htm", href)
                if not player_id_match:
                    continue

                player_id = player_id_match.group(1)

                # Get snap percentages if available
                off_snap_pct = clean_numeric(
                    self._safe_get_text(row.find("td", {"data-stat": "off_pct"}))
                )

                snap_data[player_id] = {
                    "player_id": player_id,
                    "snap_percentage": off_snap_pct or 0.0,
                }

            self.logger.info(f"Scraped snap counts for {len(snap_data)} players")

        except Exception as e:
            self.logger.error(f"Error scraping snap counts: {e}")

        return snap_data

    def scrape_player_game_log(
        self,
        player_id: str,
        season: int,
    ) -> List[GameLog]:
        """
        Scrape game-by-game log for a specific player.

        Args:
            player_id: PFR player ID
            season: NFL season year

        Returns:
            List of GameLog objects
        """
        # Get first letter of player ID for URL
        first_letter = player_id[0].upper()
        url = f"{self.base_url}/players/{first_letter}/{player_id}/gamelog/{season}/"

        game_logs = []

        try:
            response = self._fetch_page(url, "pfr", self.rate_limit_delay)
            soup = self._parse_html(response.text)

            # Find stats table
            table = soup.find("table", {"id": "stats"})
            if not table:
                self.logger.warning(f"Could not find game log table for {player_id}")
                return game_logs

            tbody = table.find("tbody")
            if not tbody:
                return game_logs

            for row in tbody.find_all("tr"):
                # Skip separator rows
                if row.get("class") and "thead" in row.get("class", []):
                    continue

                # Parse basic game info
                week_cell = row.find("td", {"data-stat": "week_num"})
                date_cell = row.find("td", {"data-stat": "game_date"})
                opp_cell = row.find("td", {"data-stat": "opp"})
                result_cell = row.find("td", {"data-stat": "game_result"})
                home_away_cell = row.find("td", {"data-stat": "game_location"})

                if not week_cell:
                    continue

                week = int(clean_numeric(self._safe_get_text(week_cell)) or 0)
                if week == 0:
                    continue

                # Build stats dict from all stat columns
                stats = {}
                for cell in row.find_all("td"):
                    stat_name = cell.get("data-stat", "")
                    if stat_name and stat_name not in ["week_num", "game_date", "opp", "game_result", "game_location"]:
                        value = clean_numeric(self._safe_get_text(cell))
                        if value is not None:
                            stats[stat_name] = value

                game_log = GameLog(
                    player_id=player_id,
                    season=season,
                    week=week,
                    date=self._safe_get_text(date_cell),
                    opponent=normalize_team(self._safe_get_text(opp_cell)),
                    home_away="away" if self._safe_get_text(home_away_cell) == "@" else "home",
                    result=self._safe_get_text(result_cell),
                    stats=stats,
                )
                game_logs.append(game_log)

            self.logger.info(f"Scraped {len(game_logs)} game logs for {player_id}")

        except Exception as e:
            self.logger.error(f"Error scraping game log for {player_id}: {e}")

        return game_logs

    def scrape_red_zone_stats(self, season: int) -> Dict[str, Dict[str, int]]:
        """
        Scrape red zone statistics.

        Args:
            season: NFL season year

        Returns:
            Dictionary mapping player IDs to red zone stats
        """
        url = f"{self.base_url}/years/{season}/redzone-receiving.htm"
        red_zone_data = {}

        try:
            response = self._fetch_page(url, "pfr", self.rate_limit_delay)
            soup = self._parse_html(response.text)

            table = soup.find("table", {"id": "redzone_receiving"})
            if not table:
                # Try comments
                comments = soup.find_all(string=lambda t: isinstance(t, Comment))
                for comment in comments:
                    if "redzone" in comment:
                        comment_soup = BeautifulSoup(comment, "lxml")
                        table = comment_soup.find("table")
                        if table:
                            break

            if table:
                tbody = table.find("tbody")
                if tbody:
                    for row in tbody.find_all("tr"):
                        player_cell = row.find("td", {"data-stat": "player"})
                        if not player_cell:
                            continue

                        player_link = player_cell.find("a")
                        if not player_link:
                            continue

                        href = player_link.get("href", "")
                        player_id_match = re.search(r"/players/\w/(\w+)\.htm", href)
                        if not player_id_match:
                            continue

                        player_id = player_id_match.group(1)

                        # Parse red zone targets and touches
                        rz_tgt = int(clean_numeric(
                            self._safe_get_text(row.find("td", {"data-stat": "rz_tgt"}))
                        ) or 0)
                        rz_rec = int(clean_numeric(
                            self._safe_get_text(row.find("td", {"data-stat": "rz_rec"}))
                        ) or 0)

                        red_zone_data[player_id] = {
                            "red_zone_targets": rz_tgt,
                            "red_zone_receptions": rz_rec,
                        }

            self.logger.info(f"Scraped red zone data for {len(red_zone_data)} players")

        except Exception as e:
            self.logger.error(f"Error scraping red zone stats: {e}")

        # Also scrape rushing red zone data
        url = f"{self.base_url}/years/{season}/redzone-rushing.htm"

        try:
            response = self._fetch_page(url, "pfr", self.rate_limit_delay)
            soup = self._parse_html(response.text)

            table = soup.find("table", {"id": "redzone_rushing"})
            if not table:
                comments = soup.find_all(string=lambda t: isinstance(t, Comment))
                for comment in comments:
                    if "redzone" in comment:
                        comment_soup = BeautifulSoup(comment, "lxml")
                        table = comment_soup.find("table")
                        if table:
                            break

            if table:
                tbody = table.find("tbody")
                if tbody:
                    for row in tbody.find_all("tr"):
                        player_cell = row.find("td", {"data-stat": "player"})
                        if not player_cell:
                            continue

                        player_link = player_cell.find("a")
                        if not player_link:
                            continue

                        href = player_link.get("href", "")
                        player_id_match = re.search(r"/players/\w/(\w+)\.htm", href)
                        if not player_id_match:
                            continue

                        player_id = player_id_match.group(1)

                        rz_att = int(clean_numeric(
                            self._safe_get_text(row.find("td", {"data-stat": "rz_att"}))
                        ) or 0)

                        if player_id in red_zone_data:
                            red_zone_data[player_id]["red_zone_rushes"] = rz_att
                        else:
                            red_zone_data[player_id] = {
                                "red_zone_targets": 0,
                                "red_zone_receptions": 0,
                                "red_zone_rushes": rz_att,
                            }

        except Exception as e:
            self.logger.error(f"Error scraping rushing red zone stats: {e}")

        return red_zone_data

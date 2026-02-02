"""
ESPN scraper for fantasy projections and injury data.

Scrapes:
- Weekly fantasy projections
- Injury reports and status
- Depth charts
- News/updates
"""
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from .base import BaseScraper
from config.settings import ScraperConfig
from utils.helpers import normalize_player_name, normalize_team, clean_numeric


@dataclass
class ESPNProjection:
    """Container for ESPN fantasy projection data."""
    player_id: str
    name: str
    team: str
    position: str
    week: int
    season: int

    # Projected stats
    projected_points: float = 0.0
    projected_passing_yards: float = 0.0
    projected_passing_tds: float = 0.0
    projected_interceptions: float = 0.0
    projected_rushing_yards: float = 0.0
    projected_rushing_tds: float = 0.0
    projected_receptions: float = 0.0
    projected_receiving_yards: float = 0.0
    projected_receiving_tds: float = 0.0

    # Ownership/start percentage
    roster_percentage: float = 0.0
    start_percentage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InjuryReport:
    """Container for injury report data."""
    player_id: str
    name: str
    team: str
    position: str
    injury_status: str  # Out, Doubtful, Questionable, Probable, IR, PUP
    injury_type: str  # e.g., "Knee", "Hamstring", etc.
    injury_details: str
    updated_at: str
    game_status: str  # Expected to play, game-time decision, etc.

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ESPNScraper(BaseScraper):
    """
    Scraper for ESPN fantasy football data.

    Uses both web scraping and ESPN's public API endpoints.
    """

    # ESPN position IDs
    POSITION_MAP = {
        1: "QB",
        2: "RB",
        3: "WR",
        4: "TE",
        5: "K",
        16: "DST",
    }

    # Reverse mapping
    POSITION_IDS = {v: k for k, v in POSITION_MAP.items()}

    # ESPN injury status mapping
    INJURY_STATUS_MAP = {
        "ACTIVE": "Active",
        "QUESTIONABLE": "Questionable",
        "DOUBTFUL": "Doubtful",
        "OUT": "Out",
        "INJURY_RESERVE": "IR",
        "PHYSICALLY_UNABLE_TO_PERFORM": "PUP",
        "SUSPENSION": "Suspended",
    }

    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config)
        self.base_url = self.config.espn_base_url
        self.api_base = self.config.espn_api_base
        self.rate_limit_delay = self.config.rate_limit_espn

    def get_data_source_name(self) -> str:
        return "ESPN"

    def scrape(
        self,
        season: int,
        week: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Scrape ESPN data for projections and injuries.

        Args:
            season: NFL season year
            week: Specific week (None for all available)

        Returns:
            Dictionary with projections and injury data
        """
        self.logger.info(f"Scraping ESPN data for {season} season, week {week}")

        results = {
            "projections": self._scrape_projections(season, week),
            "injuries": self._scrape_injuries(),
        }

        return results

    def _scrape_projections(
        self,
        season: int,
        week: Optional[int] = None,
    ) -> List[ESPNProjection]:
        """
        Scrape fantasy projections from ESPN API.

        Args:
            season: NFL season year
            week: Week number (None for season-long)

        Returns:
            List of ESPNProjection objects
        """
        projections = []

        # ESPN Fantasy API endpoint for projections
        # This uses the public fantasy API which provides projection data
        url = f"{self.api_base}/seasons/{season}/segments/0/leagues/0"

        params = {
            "view": "kona_player_info",
        }

        try:
            response = self._fetch_page(url, "espn", self.rate_limit_delay, params=params)
            data = response.json()

            players = data.get("players", [])

            for player_data in players:
                player = player_data.get("player", {})
                if not player:
                    continue

                player_id = str(player.get("id", ""))
                name = player.get("fullName", "")
                position_id = player.get("defaultPositionId", 0)
                position = self.POSITION_MAP.get(position_id, "UNKNOWN")

                # Get team
                team_abbr = ""
                if "proTeamId" in player:
                    team_abbr = self._get_team_abbr(player.get("proTeamId", 0))

                # Get projected stats
                stats = player.get("stats", [])
                projected_stats = self._extract_projected_stats(stats, season, week)

                projection = ESPNProjection(
                    player_id=player_id,
                    name=name,
                    team=normalize_team(team_abbr),
                    position=position,
                    week=week or 0,
                    season=season,
                    **projected_stats,
                )

                projections.append(projection)

            self.logger.info(f"Scraped {len(projections)} player projections")

        except Exception as e:
            self.logger.error(f"Error scraping ESPN projections: {e}")
            # Fallback to web scraping
            projections = self._scrape_projections_web(season, week)

        return projections

    def _scrape_projections_web(
        self,
        season: int,
        week: Optional[int] = None,
    ) -> List[ESPNProjection]:
        """
        Fallback web scraping for projections if API fails.
        """
        projections = []
        positions = ["qb", "rb", "wr", "te", "k", "d"]

        for pos in positions:
            url = f"{self.base_url}/fantasy/football/ffl/tools/projections"
            params = {
                "slotCategoryId": self._get_slot_category(pos),
            }
            if week:
                params["scoringPeriodId"] = week

            try:
                response = self._fetch_page(url, "espn", self.rate_limit_delay, params=params)
                soup = self._parse_html(response.text)

                # Find projection table
                table = soup.find("table", class_="Table")
                if not table:
                    continue

                tbody = table.find("tbody")
                if not tbody:
                    continue

                for row in tbody.find_all("tr"):
                    cells = row.find_all("td")
                    if len(cells) < 2:
                        continue

                    # Parse player info from first cell
                    player_cell = cells[0]
                    player_link = player_cell.find("a")
                    if not player_link:
                        continue

                    name = self._safe_get_text(player_link)

                    # Extract player ID from href
                    href = player_link.get("href", "")
                    player_id_match = re.search(r"/id/(\d+)/", href)
                    player_id = player_id_match.group(1) if player_id_match else ""

                    # Get team from player cell
                    team_span = player_cell.find("span", class_="playerinfo__playerteam")
                    team = normalize_team(self._safe_get_text(team_span))

                    # Get projected points (usually last column)
                    projected_points = clean_numeric(
                        self._safe_get_text(cells[-1])
                    ) or 0.0

                    projection = ESPNProjection(
                        player_id=player_id,
                        name=name,
                        team=team,
                        position=pos.upper(),
                        week=week or 0,
                        season=season,
                        projected_points=projected_points,
                    )
                    projections.append(projection)

            except Exception as e:
                self.logger.error(f"Error scraping {pos} projections: {e}")
                continue

        return projections

    def _scrape_injuries(self) -> List[InjuryReport]:
        """
        Scrape NFL injury reports from ESPN.

        Returns:
            List of InjuryReport objects
        """
        injuries = []

        # ESPN injuries page
        url = f"{self.base_url}/injuries"

        try:
            response = self._fetch_page(url, "espn", self.rate_limit_delay)
            soup = self._parse_html(response.text)

            # Find injury tables by team
            injury_sections = soup.find_all("div", class_="ResponsiveTable")

            for section in injury_sections:
                # Get team name from section header
                header = section.find_previous("h2")
                team = normalize_team(self._safe_get_text(header)) if header else ""

                table = section.find("table")
                if not table:
                    continue

                tbody = table.find("tbody")
                if not tbody:
                    continue

                for row in tbody.find_all("tr"):
                    cells = row.find_all("td")
                    if len(cells) < 4:
                        continue

                    # Parse player info
                    player_cell = cells[0]
                    player_link = player_cell.find("a")

                    if player_link:
                        name = self._safe_get_text(player_link)
                        href = player_link.get("href", "")
                        player_id_match = re.search(r"/id/(\d+)/", href)
                        player_id = player_id_match.group(1) if player_id_match else ""
                    else:
                        name = self._safe_get_text(player_cell)
                        player_id = ""

                    # Parse position
                    position = self._safe_get_text(cells[1]) if len(cells) > 1 else ""

                    # Parse injury details
                    injury_type = self._safe_get_text(cells[2]) if len(cells) > 2 else ""
                    status = self._safe_get_text(cells[3]) if len(cells) > 3 else ""

                    injury = InjuryReport(
                        player_id=player_id,
                        name=name,
                        team=team,
                        position=position.upper(),
                        injury_status=self._normalize_injury_status(status),
                        injury_type=injury_type,
                        injury_details="",
                        updated_at=datetime.now().isoformat(),
                        game_status=self._get_game_status(status),
                    )
                    injuries.append(injury)

            self.logger.info(f"Scraped {len(injuries)} injury reports")

        except Exception as e:
            self.logger.error(f"Error scraping ESPN injuries: {e}")

        return injuries

    def scrape_depth_charts(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scrape NFL depth charts from ESPN.

        Returns:
            Dictionary mapping teams to their depth charts
        """
        depth_charts = {}

        url = f"{self.base_url}/depth"

        try:
            response = self._fetch_page(url, "espn", self.rate_limit_delay)
            soup = self._parse_html(response.text)

            # Find team depth chart sections
            team_sections = soup.find_all("div", class_="DepthChart")

            for section in team_sections:
                team_header = section.find("a", class_="TeamLink")
                if not team_header:
                    continue

                team = normalize_team(self._safe_get_text(team_header))
                depth_charts[team] = []

                # Parse positions
                positions = section.find_all("div", class_="DepthChart__Position")

                for pos_section in positions:
                    pos_header = pos_section.find("span", class_="position")
                    position = self._safe_get_text(pos_header)

                    players = pos_section.find_all("a", class_="AnchorLink")

                    for depth, player_link in enumerate(players, 1):
                        name = self._safe_get_text(player_link)
                        href = player_link.get("href", "")
                        player_id_match = re.search(r"/id/(\d+)/", href)
                        player_id = player_id_match.group(1) if player_id_match else ""

                        depth_charts[team].append({
                            "player_id": player_id,
                            "name": name,
                            "position": position,
                            "depth": depth,
                        })

            self.logger.info(f"Scraped depth charts for {len(depth_charts)} teams")

        except Exception as e:
            self.logger.error(f"Error scraping depth charts: {e}")

        return depth_charts

    def _extract_projected_stats(
        self,
        stats: List[Dict],
        season: int,
        week: Optional[int],
    ) -> Dict[str, float]:
        """
        Extract projected stats from ESPN stats array.

        Args:
            stats: List of stat objects from API
            season: NFL season year
            week: Week number

        Returns:
            Dictionary of projected stats
        """
        result = {
            "projected_points": 0.0,
            "projected_passing_yards": 0.0,
            "projected_passing_tds": 0.0,
            "projected_interceptions": 0.0,
            "projected_rushing_yards": 0.0,
            "projected_rushing_tds": 0.0,
            "projected_receptions": 0.0,
            "projected_receiving_yards": 0.0,
            "projected_receiving_tds": 0.0,
            "roster_percentage": 0.0,
            "start_percentage": 0.0,
        }

        for stat in stats:
            # ESPN stat source types
            # 0 = season projections, 1 = season actuals
            # Week projections have scoringPeriodId set
            stat_source = stat.get("statSourceId", 1)
            stat_split = stat.get("statSplitTypeId", 0)

            # Look for projections (statSourceId = 1 for ESPN projections)
            if stat_source != 1:
                continue

            # Check if this is the right period
            if week and stat.get("scoringPeriodId") != week:
                continue

            applied_stats = stat.get("stats", {})

            # ESPN stat IDs mapping (approximate - actual IDs may vary)
            # Passing: 0=attempts, 1=completions, 3=yards, 4=TDs, 20=INTs
            # Rushing: 23=attempts, 24=yards, 25=TDs
            # Receiving: 41=receptions, 42=yards, 43=TDs

            result["projected_passing_yards"] = applied_stats.get("3", 0.0)
            result["projected_passing_tds"] = applied_stats.get("4", 0.0)
            result["projected_interceptions"] = applied_stats.get("20", 0.0)
            result["projected_rushing_yards"] = applied_stats.get("24", 0.0)
            result["projected_rushing_tds"] = applied_stats.get("25", 0.0)
            result["projected_receptions"] = applied_stats.get("41", 0.0)
            result["projected_receiving_yards"] = applied_stats.get("42", 0.0)
            result["projected_receiving_tds"] = applied_stats.get("43", 0.0)

            # Applied total is the projected fantasy points
            result["projected_points"] = stat.get("appliedTotal", 0.0)

        return result

    def _get_team_abbr(self, team_id: int) -> str:
        """Map ESPN team ID to abbreviation."""
        team_map = {
            1: "ATL", 2: "BUF", 3: "CHI", 4: "CIN", 5: "CLE",
            6: "DAL", 7: "DEN", 8: "DET", 9: "GB", 10: "TEN",
            11: "IND", 12: "KC", 13: "LV", 14: "LAR", 15: "MIA",
            16: "MIN", 17: "NE", 18: "NO", 19: "NYG", 20: "NYJ",
            21: "PHI", 22: "ARI", 23: "PIT", 24: "LAC", 25: "SF",
            26: "SEA", 27: "TB", 28: "WAS", 29: "CAR", 30: "JAX",
            33: "BAL", 34: "HOU",
        }
        return team_map.get(team_id, "")

    def _get_slot_category(self, position: str) -> int:
        """Map position to ESPN slot category ID."""
        slot_map = {
            "qb": 0,
            "rb": 2,
            "wr": 4,
            "te": 6,
            "k": 17,
            "d": 16,
            "dst": 16,
        }
        return slot_map.get(position.lower(), 0)

    def _normalize_injury_status(self, status: str) -> str:
        """Normalize injury status to standard format."""
        status_lower = status.lower().strip()

        if "out" in status_lower:
            return "Out"
        elif "doubtful" in status_lower:
            return "Doubtful"
        elif "questionable" in status_lower:
            return "Questionable"
        elif "probable" in status_lower:
            return "Probable"
        elif "ir" in status_lower or "injured reserve" in status_lower:
            return "IR"
        elif "pup" in status_lower:
            return "PUP"
        elif "suspended" in status_lower:
            return "Suspended"
        else:
            return "Unknown"

    def _get_game_status(self, status: str) -> str:
        """Determine expected game status from injury status."""
        normalized = self._normalize_injury_status(status)

        status_map = {
            "Out": "Will not play",
            "Doubtful": "Unlikely to play",
            "Questionable": "Game-time decision",
            "Probable": "Expected to play",
            "IR": "Will not play",
            "PUP": "Will not play",
            "Suspended": "Will not play",
        }

        return status_map.get(normalized, "Unknown")

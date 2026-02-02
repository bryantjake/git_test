"""
Scraper orchestration module.

Coordinates all data scrapers and handles:
- Running scrapers in sequence with rate limiting
- Storing data in the database
- Error handling and retries
- Logging and reporting
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .pro_football_reference import ProFootballReferenceScraper, PlayerStats
from .espn import ESPNScraper, ESPNProjection, InjuryReport
from .vegas import VegasScraper, GameLines

from database.models import (
    init_db,
    session_scope,
    get_or_create_player,
    Player,
    PlayerStats as DBPlayerStats,
    WeeklyStats,
    Projection,
    Injury,
    GameOdds,
)
from config.settings import ScraperConfig, DEFAULT_SCRAPER
from utils.helpers import (
    get_current_nfl_season,
    get_current_nfl_week,
    normalize_team,
    calculate_fantasy_points,
)

logger = logging.getLogger(__name__)


class ScraperOrchestrator:
    """
    Orchestrates all data scraping operations.

    Handles running scrapers, processing data, and storing results.
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize the orchestrator.

        Args:
            config: Scraper configuration
        """
        self.config = config or DEFAULT_SCRAPER
        self.pfr_scraper = ProFootballReferenceScraper(config)
        self.espn_scraper = ESPNScraper(config)
        self.vegas_scraper = VegasScraper(config)

        # Initialize database
        init_db()

    def run_full_update(
        self,
        season: Optional[int] = None,
        week: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run a full data update from all sources.

        Args:
            season: NFL season year (defaults to current)
            week: Week number (defaults to current)

        Returns:
            Summary of update results
        """
        if season is None:
            season = get_current_nfl_season()
        if week is None:
            week = get_current_nfl_week(season)

        logger.info(f"Starting full update for {season} season, week {week}")

        results = {
            "season": season,
            "week": week,
            "started_at": datetime.utcnow().isoformat(),
            "pfr_stats": {"success": False, "count": 0, "error": None},
            "espn_projections": {"success": False, "count": 0, "error": None},
            "espn_injuries": {"success": False, "count": 0, "error": None},
            "vegas_lines": {"success": False, "count": 0, "error": None},
        }

        # Scrape Pro Football Reference stats
        try:
            pfr_results = self._scrape_pfr_stats(season)
            results["pfr_stats"]["success"] = True
            results["pfr_stats"]["count"] = pfr_results
        except Exception as e:
            logger.error(f"PFR scraping failed: {e}")
            results["pfr_stats"]["error"] = str(e)

        # Scrape ESPN projections and injuries
        try:
            espn_results = self._scrape_espn_data(season, week)
            results["espn_projections"]["success"] = True
            results["espn_projections"]["count"] = espn_results["projections"]
            results["espn_injuries"]["success"] = True
            results["espn_injuries"]["count"] = espn_results["injuries"]
        except Exception as e:
            logger.error(f"ESPN scraping failed: {e}")
            results["espn_projections"]["error"] = str(e)
            results["espn_injuries"]["error"] = str(e)

        # Scrape Vegas lines
        try:
            vegas_results = self._scrape_vegas_lines(season, week)
            results["vegas_lines"]["success"] = True
            results["vegas_lines"]["count"] = vegas_results
        except Exception as e:
            logger.error(f"Vegas lines scraping failed: {e}")
            results["vegas_lines"]["error"] = str(e)

        results["completed_at"] = datetime.utcnow().isoformat()
        logger.info(f"Full update completed: {results}")

        return results

    def _scrape_pfr_stats(self, season: int) -> int:
        """
        Scrape and store Pro Football Reference stats.

        Args:
            season: NFL season year

        Returns:
            Number of players processed
        """
        logger.info(f"Scraping PFR stats for {season}")

        with self.pfr_scraper as scraper:
            stats_data = scraper.scrape(season)
            snap_data = scraper.scrape_snap_counts(season)
            red_zone_data = scraper.scrape_red_zone_stats(season)

        total_processed = 0

        with session_scope() as session:
            # Process each category of stats
            for category, players in stats_data.items():
                for player_stats in players:
                    self._store_player_stats(
                        session,
                        player_stats,
                        season,
                        snap_data,
                        red_zone_data,
                    )
                    total_processed += 1

        logger.info(f"Processed {total_processed} players from PFR")
        return total_processed

    def _store_player_stats(
        self,
        session,
        stats: PlayerStats,
        season: int,
        snap_data: Dict[str, Any],
        red_zone_data: Dict[str, Any],
    ) -> None:
        """
        Store player stats in database.

        Args:
            session: Database session
            stats: PlayerStats object
            season: NFL season year
            snap_data: Snap count data dictionary
            red_zone_data: Red zone stats dictionary
        """
        # Get or create player
        player = get_or_create_player(
            session,
            name=stats.name,
            team=stats.team,
            position=stats.position,
            pfr_id=stats.player_id,
        )

        # Check for existing season stats
        existing_stats = session.query(DBPlayerStats).filter(
            DBPlayerStats.player_id == player.id,
            DBPlayerStats.season == season,
        ).first()

        # Get additional data
        player_snap_data = snap_data.get(stats.player_id, {})
        player_rz_data = red_zone_data.get(stats.player_id, {})

        # Calculate fantasy points
        stats_dict = stats.to_dict()
        fp_standard = calculate_fantasy_points(stats_dict, ppr_value=0.0)
        fp_half_ppr = calculate_fantasy_points(stats_dict, ppr_value=0.5)
        fp_ppr = calculate_fantasy_points(stats_dict, ppr_value=1.0)

        if existing_stats:
            # Update existing record
            existing_stats.games_played = stats.games_played
            existing_stats.games_started = stats.games_started
            existing_stats.passing_attempts = stats.passing_attempts
            existing_stats.passing_completions = stats.passing_completions
            existing_stats.passing_yards = stats.passing_yards
            existing_stats.passing_tds = stats.passing_tds
            existing_stats.interceptions = stats.interceptions
            existing_stats.rushing_attempts = stats.rushing_attempts
            existing_stats.rushing_yards = stats.rushing_yards
            existing_stats.rushing_tds = stats.rushing_tds
            existing_stats.targets = stats.targets
            existing_stats.receptions = stats.receptions
            existing_stats.receiving_yards = stats.receiving_yards
            existing_stats.receiving_tds = stats.receiving_tds
            existing_stats.snap_percentage = player_snap_data.get("snap_percentage", 0.0)
            existing_stats.red_zone_targets = player_rz_data.get("red_zone_targets", 0)
            existing_stats.red_zone_touches = player_rz_data.get("red_zone_rushes", 0)
            existing_stats.fantasy_points_standard = fp_standard
            existing_stats.fantasy_points_half_ppr = fp_half_ppr
            existing_stats.fantasy_points_ppr = fp_ppr
        else:
            # Create new record
            db_stats = DBPlayerStats(
                player_id=player.id,
                season=season,
                games_played=stats.games_played,
                games_started=stats.games_started,
                passing_attempts=stats.passing_attempts,
                passing_completions=stats.passing_completions,
                passing_yards=stats.passing_yards,
                passing_tds=stats.passing_tds,
                interceptions=stats.interceptions,
                rushing_attempts=stats.rushing_attempts,
                rushing_yards=stats.rushing_yards,
                rushing_tds=stats.rushing_tds,
                targets=stats.targets,
                receptions=stats.receptions,
                receiving_yards=stats.receiving_yards,
                receiving_tds=stats.receiving_tds,
                snap_percentage=player_snap_data.get("snap_percentage", 0.0),
                red_zone_targets=player_rz_data.get("red_zone_targets", 0),
                red_zone_touches=player_rz_data.get("red_zone_rushes", 0),
                fantasy_points_standard=fp_standard,
                fantasy_points_half_ppr=fp_half_ppr,
                fantasy_points_ppr=fp_ppr,
            )
            session.add(db_stats)

    def _scrape_espn_data(
        self,
        season: int,
        week: int,
    ) -> Dict[str, int]:
        """
        Scrape and store ESPN data.

        Args:
            season: NFL season year
            week: Week number

        Returns:
            Dictionary with counts of data processed
        """
        logger.info(f"Scraping ESPN data for {season} week {week}")

        with self.espn_scraper as scraper:
            espn_data = scraper.scrape(season, week)

        projections_count = 0
        injuries_count = 0

        with session_scope() as session:
            # Store projections
            for projection in espn_data.get("projections", []):
                self._store_projection(session, projection, season, week)
                projections_count += 1

            # Store injuries
            for injury in espn_data.get("injuries", []):
                self._store_injury(session, injury, season, week)
                injuries_count += 1

        logger.info(f"Processed {projections_count} projections, {injuries_count} injuries")
        return {"projections": projections_count, "injuries": injuries_count}

    def _store_projection(
        self,
        session,
        projection: ESPNProjection,
        season: int,
        week: int,
    ) -> None:
        """
        Store ESPN projection in database.

        Args:
            session: Database session
            projection: ESPNProjection object
            season: NFL season year
            week: Week number
        """
        # Get or create player
        player = get_or_create_player(
            session,
            name=projection.name,
            team=projection.team,
            position=projection.position,
            espn_id=projection.player_id,
        )

        # Check for existing projection
        existing = session.query(Projection).filter(
            Projection.player_id == player.id,
            Projection.season == season,
            Projection.week == week,
            Projection.source == "ESPN",
        ).first()

        if existing:
            existing.projected_points = projection.projected_points
            existing.projected_passing_yards = projection.projected_passing_yards
            existing.projected_passing_tds = projection.projected_passing_tds
            existing.projected_interceptions = projection.projected_interceptions
            existing.projected_rushing_yards = projection.projected_rushing_yards
            existing.projected_rushing_tds = projection.projected_rushing_tds
            existing.projected_receptions = projection.projected_receptions
            existing.projected_receiving_yards = projection.projected_receiving_yards
            existing.projected_receiving_tds = projection.projected_receiving_tds
            existing.roster_percentage = projection.roster_percentage
            existing.start_percentage = projection.start_percentage
        else:
            db_projection = Projection(
                player_id=player.id,
                season=season,
                week=week,
                source="ESPN",
                projected_points=projection.projected_points,
                projected_passing_yards=projection.projected_passing_yards,
                projected_passing_tds=projection.projected_passing_tds,
                projected_interceptions=projection.projected_interceptions,
                projected_rushing_yards=projection.projected_rushing_yards,
                projected_rushing_tds=projection.projected_rushing_tds,
                projected_receptions=projection.projected_receptions,
                projected_receiving_yards=projection.projected_receiving_yards,
                projected_receiving_tds=projection.projected_receiving_tds,
                roster_percentage=projection.roster_percentage,
                start_percentage=projection.start_percentage,
            )
            session.add(db_projection)

    def _store_injury(
        self,
        session,
        injury: InjuryReport,
        season: int,
        week: int,
    ) -> None:
        """
        Store injury report in database.

        Args:
            session: Database session
            injury: InjuryReport object
            season: NFL season year
            week: Week number
        """
        # Get or create player
        player = get_or_create_player(
            session,
            name=injury.name,
            team=injury.team,
            position=injury.position,
            espn_id=injury.player_id,
        )

        # Create new injury report (we want to track history)
        db_injury = Injury(
            player_id=player.id,
            season=season,
            week=week,
            injury_status=injury.injury_status,
            injury_type=injury.injury_type,
            injury_details=injury.injury_details,
            game_status=injury.game_status,
        )
        session.add(db_injury)

    def _scrape_vegas_lines(
        self,
        season: int,
        week: int,
    ) -> int:
        """
        Scrape and store Vegas lines.

        Args:
            season: NFL season year
            week: Week number

        Returns:
            Number of games processed
        """
        logger.info(f"Scraping Vegas lines for {season} week {week}")

        with self.vegas_scraper as scraper:
            games = scraper.scrape(season, week)

        with session_scope() as session:
            for game in games:
                self._store_game_odds(session, game, season, week)

        logger.info(f"Processed {len(games)} game odds")
        return len(games)

    def _store_game_odds(
        self,
        session,
        game: GameLines,
        season: int,
        week: int,
    ) -> None:
        """
        Store game odds in database.

        Args:
            session: Database session
            game: GameLines object
            season: NFL season year
            week: Week number
        """
        # Check for existing odds
        existing = session.query(GameOdds).filter(
            GameOdds.season == season,
            GameOdds.week == week,
            GameOdds.home_team == game.home_team,
        ).first()

        if existing:
            existing.spread = game.spread
            existing.over_under = game.over_under
            existing.home_implied_total = game.home_implied_total
            existing.away_implied_total = game.away_implied_total
            existing.home_moneyline = game.home_moneyline
            existing.away_moneyline = game.away_moneyline
            existing.home_win_probability = game.home_win_probability
            existing.away_win_probability = game.away_win_probability
        else:
            db_odds = GameOdds(
                game_id=game.game_id,
                season=season,
                week=week,
                home_team=game.home_team,
                away_team=game.away_team,
                spread=game.spread,
                over_under=game.over_under,
                home_implied_total=game.home_implied_total,
                away_implied_total=game.away_implied_total,
                home_moneyline=game.home_moneyline,
                away_moneyline=game.away_moneyline,
                home_win_probability=game.home_win_probability,
                away_win_probability=game.away_win_probability,
            )
            session.add(db_odds)

    def close(self) -> None:
        """Close all scraper connections."""
        self.pfr_scraper.close()
        self.espn_scraper.close()
        self.vegas_scraper.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def run_daily_update() -> Dict[str, Any]:
    """
    Convenience function to run daily update.

    Returns:
        Update results dictionary
    """
    with ScraperOrchestrator() as orchestrator:
        return orchestrator.run_full_update()


if __name__ == "__main__":
    # Run update when called directly
    logging.basicConfig(level=logging.INFO)
    results = run_daily_update()
    print(f"Update completed: {results}")

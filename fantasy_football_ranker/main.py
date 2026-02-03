#!/usr/bin/env python3
"""
Fantasy Football Ranker - Main Entry Point

A comprehensive fantasy football ranking system that:
- Scrapes data from Pro Football Reference, ESPN, and Vegas lines
- Stores data in SQLite database
- Calculates advanced rankings using VORP, Bayesian updating, and more
- Outputs rankings to premium terminal display or web dashboard
"""
import argparse
import logging
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    DEFAULT_LEAGUE,
    LEAGUE_PRESETS,
    DATA_DIR,
    OUTPUT_DIR,
)
from database.models import (
    init_db,
    get_session,
    Player,
    PlayerStats,
    WeeklyStats,
    Projection,
    Injury,
    GameOdds,
    Ranking,
)
from utils.helpers import get_current_nfl_season, get_current_nfl_week

# Set up logger
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO

    # Ensure data directory exists for log file
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(DATA_DIR / "fantasy_football.log"),
        ],
    )


def load_players_from_db(session, season: int) -> List[Dict]:
    """Load player data from database into dictionaries for ranking."""
    players = []

    # Query players with their stats
    query = session.query(Player).join(
        PlayerStats, Player.id == PlayerStats.player_id, isouter=True
    ).filter(PlayerStats.season == season)

    for player in session.query(Player).all():
        # Get season stats
        stats = session.query(PlayerStats).filter(
            PlayerStats.player_id == player.id,
            PlayerStats.season == season
        ).first()

        if not stats:
            continue

        # Get latest injury
        injury = session.query(Injury).filter(
            Injury.player_id == player.id
        ).order_by(Injury.report_date.desc()).first()

        player_dict = {
            "player_id": player.id,
            "name": player.name,
            "team": player.team or "",
            "position": player.position or "",
            "age": player.age or 25,
            "experience": player.experience or 3,
            "games_played": stats.games_played,
            "games_started": stats.games_started,
            "passing_attempts": stats.passing_attempts,
            "passing_completions": stats.passing_completions,
            "passing_yards": stats.passing_yards,
            "passing_tds": stats.passing_tds,
            "interceptions": stats.interceptions,
            "rushing_attempts": stats.rushing_attempts,
            "rushing_yards": stats.rushing_yards,
            "rushing_tds": stats.rushing_tds,
            "targets": stats.targets,
            "receptions": stats.receptions,
            "receiving_yards": stats.receiving_yards,
            "receiving_tds": stats.receiving_tds,
            "snap_percentage": stats.snap_percentage,
            "red_zone_targets": stats.red_zone_targets,
            "red_zone_touches": stats.red_zone_touches,
            "fantasy_points": stats.fantasy_points_ppr,
            "ppg": stats.fantasy_points_ppr / max(stats.games_played, 1),
            "injury_status": injury.injury_status if injury else "Healthy",
        }
        players.append(player_dict)

    return players


def load_weekly_scores(session, season: int) -> Dict[int, List[float]]:
    """Load weekly scores for all players."""
    weekly_scores = {}

    for weekly in session.query(WeeklyStats).filter(WeeklyStats.season == season).all():
        if weekly.player_id not in weekly_scores:
            weekly_scores[weekly.player_id] = []
        weekly_scores[weekly.player_id].append(weekly.fantasy_points_ppr)

    return weekly_scores


def load_projections(session, season: int) -> Dict[int, float]:
    """Load projections for all players."""
    projections = {}

    for proj in session.query(Projection).filter(Projection.season == season).all():
        projections[proj.player_id] = proj.projected_points

    return projections


def load_game_odds(session, season: int, week: int) -> Dict[str, Dict]:
    """Load game odds for teams."""
    odds = {}

    for game in session.query(GameOdds).filter(
        GameOdds.season == season,
        GameOdds.week == week
    ).all():
        odds[game.home_team] = {
            "implied_total": game.home_implied_total,
            "spread": -game.spread,
            "over_under": game.over_under,
            "is_home": True,
            "week": week,
        }
        odds[game.away_team] = {
            "implied_total": game.away_implied_total,
            "spread": game.spread,
            "over_under": game.over_under,
            "is_home": False,
            "week": week,
        }

    return odds


def generate_sample_data() -> tuple:
    """Generate sample data for testing/demo."""
    import random

    positions = ["QB", "RB", "WR", "TE"]
    teams = ["KC", "SF", "PHI", "DAL", "MIA", "BUF", "CIN", "DET", "BAL", "JAX"]

    # Sample player names by position
    player_names = {
        "QB": ["Patrick Mahomes", "Josh Allen", "Jalen Hurts", "Lamar Jackson", "Joe Burrow",
               "Tua Tagovailoa", "Dak Prescott", "Justin Herbert", "Trevor Lawrence", "Jared Goff"],
        "RB": ["Christian McCaffrey", "Austin Ekeler", "Bijan Robinson", "Tony Pollard", "Travis Etienne",
               "Saquon Barkley", "Nick Chubb", "Josh Jacobs", "Derrick Henry", "Jahmyr Gibbs",
               "Rhamondre Stevenson", "Aaron Jones", "Joe Mixon", "Breece Hall", "Jonathan Taylor"],
        "WR": ["Tyreek Hill", "Justin Jefferson", "CeeDee Lamb", "Ja'Marr Chase", "Amon-Ra St. Brown",
               "AJ Brown", "Davante Adams", "Stefon Diggs", "Garrett Wilson", "DeVonta Smith",
               "Chris Olave", "DK Metcalf", "Jaylen Waddle", "Amari Cooper", "Brandon Aiyuk"],
        "TE": ["Travis Kelce", "TJ Hockenson", "Mark Andrews", "George Kittle", "Dallas Goedert",
               "Evan Engram", "David Njoku", "Sam LaPorta", "Kyle Pitts", "Dalton Kincaid"],
    }

    players = []
    player_id = 1

    for pos, names in player_names.items():
        for i, name in enumerate(names):
            # Generate realistic stats based on position rank
            rank_factor = 1.0 - (i * 0.06)  # Decreasing quality

            if pos == "QB":
                ppg = random.uniform(15, 25) * rank_factor
                pass_yds = int(random.uniform(3500, 4500) * rank_factor)
                pass_tds = int(random.uniform(25, 35) * rank_factor)
            elif pos == "RB":
                ppg = random.uniform(10, 20) * rank_factor
                rush_yds = int(random.uniform(800, 1400) * rank_factor)
                rush_tds = int(random.uniform(6, 14) * rank_factor)
                rec = int(random.uniform(30, 70) * rank_factor)
            elif pos == "WR":
                ppg = random.uniform(10, 18) * rank_factor
                rec_yds = int(random.uniform(900, 1400) * rank_factor)
                rec_tds = int(random.uniform(5, 12) * rank_factor)
                targets = int(random.uniform(100, 160) * rank_factor)
            else:  # TE
                ppg = random.uniform(8, 15) * rank_factor
                rec_yds = int(random.uniform(500, 1000) * rank_factor)
                rec_tds = int(random.uniform(4, 10) * rank_factor)
                targets = int(random.uniform(70, 120) * rank_factor)

            games = random.randint(14, 17)

            player = {
                "player_id": player_id,
                "name": name,
                "team": random.choice(teams),
                "position": pos,
                "age": random.randint(23, 32),
                "experience": random.randint(1, 10),
                "games_played": games,
                "games_started": games - random.randint(0, 2),
                "passing_attempts": int(random.uniform(450, 600)) if pos == "QB" else 0,
                "passing_completions": int(random.uniform(280, 400)) if pos == "QB" else 0,
                "passing_yards": pass_yds if pos == "QB" else 0,
                "passing_tds": pass_tds if pos == "QB" else 0,
                "interceptions": random.randint(5, 15) if pos == "QB" else 0,
                "rushing_attempts": int(random.uniform(150, 280) * rank_factor) if pos == "RB" else random.randint(0, 50),
                "rushing_yards": rush_yds if pos == "RB" else random.randint(0, 300),
                "rushing_tds": rush_tds if pos == "RB" else random.randint(0, 3),
                "targets": targets if pos in ["WR", "TE"] else int(random.uniform(40, 80) * rank_factor) if pos == "RB" else 0,
                "receptions": rec if pos == "RB" else int(random.uniform(60, 120) * rank_factor) if pos in ["WR", "TE"] else 0,
                "receiving_yards": rec_yds if pos in ["WR", "TE"] else int(random.uniform(200, 500) * rank_factor) if pos == "RB" else 0,
                "receiving_tds": rec_tds if pos in ["WR", "TE"] else random.randint(0, 4) if pos == "RB" else 0,
                "snap_percentage": random.uniform(60, 95) * rank_factor,
                "red_zone_targets": int(random.uniform(10, 30) * rank_factor),
                "red_zone_touches": int(random.uniform(20, 50) * rank_factor) if pos == "RB" else int(random.uniform(5, 15) * rank_factor),
                "fantasy_points": ppg * games,
                "ppg": ppg,
                "injury_status": random.choice(["Healthy"] * 8 + ["Questionable", "Probable"]),
            }
            players.append(player)
            player_id += 1

    # Generate weekly scores (random variation around PPG)
    weekly_scores = {}
    for player in players:
        scores = []
        for _ in range(player["games_played"]):
            variance = random.uniform(0.5, 1.5)
            scores.append(player["ppg"] * variance)
        weekly_scores[player["player_id"]] = scores

    # Generate projections (slightly optimistic)
    projections = {
        p["player_id"]: p["ppg"] * random.uniform(0.95, 1.1)
        for p in players
    }

    # Generate game odds
    game_odds = {}
    for team in teams:
        game_odds[team] = {
            "implied_total": random.uniform(20, 28),
            "spread": random.uniform(-7, 7),
            "over_under": random.uniform(42, 52),
            "is_home": random.choice([True, False]),
            "week": 10,
        }

    return players, weekly_scores, projections, game_odds


def cmd_scrape(args) -> None:
    """Run data scraping."""
    from scrapers.orchestrator import ScraperOrchestrator

    logger.info(f"Starting scrape for season {args.season}, week {args.week}")

    with ScraperOrchestrator() as orchestrator:
        results = orchestrator.run_full_update(
            season=args.season,
            week=args.week,
        )

    logger.info(f"Scrape completed: {results}")

    # Print summary
    print("\n=== Scrape Summary ===")
    print(f"Season: {results['season']}, Week: {results['week']}")
    print(f"PFR Stats: {results['pfr_stats']['count']} players")
    print(f"ESPN Projections: {results['espn_projections']['count']} players")
    print(f"ESPN Injuries: {results['espn_injuries']['count']} reports")
    print(f"Vegas Lines: {results['vegas_lines']['count']} games")

    # Report any errors
    for source, data in results.items():
        if isinstance(data, dict) and data.get("error"):
            print(f"WARNING: {source} error: {data['error']}")


def cmd_rank(args) -> None:
    """Generate rankings."""
    from ranking import RankingEngine, RankingResults
    from output import PremiumConsole

    logger.info(f"Generating rankings for {args.format} format")

    season = args.season
    week = args.week or get_current_nfl_week(season)

    # Get league settings
    league_settings = LEAGUE_PRESETS.get(args.format, DEFAULT_LEAGUE)

    # Load data from database
    session = get_session()

    try:
        players = load_players_from_db(session, season)

        if not players:
            print("No player data found in database.")
            print("Run 'python main.py demo' to generate sample rankings,")
            print("or 'python main.py scrape' to fetch real data.")
            return

        weekly_scores = load_weekly_scores(session, season)
        projections = load_projections(session, season)
        game_odds = load_game_odds(session, season, week)
        injury_history = {}  # Would load from injury table

        # Generate rankings
        engine = RankingEngine(league_settings=league_settings)
        results = engine.generate_rankings(
            players=players,
            weekly_scores=weekly_scores,
            projections=projections,
            injury_history=injury_history,
            game_odds=game_odds,
            current_week=week,
            season=season,
        )

        # Display results
        console = PremiumConsole()
        console.print_summary(results)
        console.print_rankings_table(results.overall_rankings[:30], "Overall Rankings")

        # Save to file
        output_file = OUTPUT_DIR / f"rankings_{season}_week{week}_{args.format}.json"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        rankings_data = [r.to_dict() for r in results.overall_rankings]
        with open(output_file, "w") as f:
            json.dump(rankings_data, f, indent=2)

        print(f"\nRankings saved to: {output_file}")

    finally:
        session.close()


def cmd_demo(args) -> None:
    """Run demo with sample data."""
    from ranking import RankingEngine
    from output import PremiumConsole

    print("Generating sample data for demo...")

    # Generate sample data
    players, weekly_scores, projections, game_odds = generate_sample_data()

    # Get league settings
    league_settings = LEAGUE_PRESETS.get(args.format, DEFAULT_LEAGUE)

    # Generate rankings
    engine = RankingEngine(league_settings=league_settings)
    results = engine.generate_rankings(
        players=players,
        weekly_scores=weekly_scores,
        projections=projections,
        injury_history={},
        game_odds=game_odds,
        current_week=10,
        season=2024,
    )

    # Display results
    console = PremiumConsole()
    console.print_summary(results)

    if args.position:
        # Show specific position
        pos_rankings = results.get_position_rankings(args.position.upper())
        console.print_rankings_table(
            pos_rankings[:20],
            f"{args.position.upper()} Rankings"
        )
        console.print_tier_visualization(results, args.position.upper())
    else:
        # Show overall
        console.print_rankings_table(results.overall_rankings[:30], "Overall Rankings")

    if args.compare:
        # Compare specific players
        names = [n.strip() for n in args.compare.split(",")]
        to_compare = [r for r in results.overall_rankings if r.name in names]
        if to_compare:
            print("\n")
            console.print_comparison(to_compare)

    # Show top 3 player cards
    if args.cards:
        print("\n")
        for ranking in results.overall_rankings[:3]:
            console.print_player_card(ranking)


def cmd_show(args) -> None:
    """Display rankings from saved file or database."""
    from output import PremiumConsole

    # Try to load from most recent rankings file
    rankings_files = list(OUTPUT_DIR.glob("rankings_*.json"))

    if not rankings_files:
        print("No saved rankings found.")
        print("Run 'python main.py rank' to generate rankings first.")
        return

    # Get most recent file
    latest_file = max(rankings_files, key=lambda f: f.stat().st_mtime)
    print(f"Loading rankings from: {latest_file}")

    with open(latest_file) as f:
        rankings_data = json.load(f)

    # Convert to simple display format
    console = PremiumConsole()

    # Create a simple table
    from rich.table import Table
    from rich.panel import Panel

    table = Table(title="Saved Rankings", show_lines=True)
    table.add_column("Rank", justify="center", width=6)
    table.add_column("Player", justify="left", min_width=20)
    table.add_column("Pos", justify="center", width=5)
    table.add_column("Team", justify="center", width=6)
    table.add_column("Projected", justify="right", width=10)
    table.add_column("Score", justify="right", width=8)

    for r in rankings_data[:args.limit]:
        table.add_row(
            str(r.get("rank", "")),
            r.get("name", ""),
            r.get("position", ""),
            r.get("team", ""),
            f"{r.get('projected_points', 0):.1f}",
            f"{r.get('composite_score', 0):.0f}",
        )

    console.console.print(table)


def cmd_schedule(args) -> None:
    """Set up and run scheduled tasks."""
    import schedule

    print(f"Setting up daily update schedule at {args.time}")
    print("Press Ctrl+C to stop.\n")

    def job():
        print(f"\n[{datetime.now()}] Running scheduled update...")
        try:
            from scrapers.orchestrator import run_daily_update
            results = run_daily_update()
            print(f"Update completed: {results['pfr_stats']['count']} players scraped")
        except Exception as e:
            print(f"Error during scheduled update: {e}")

    # Schedule the job
    schedule.every().day.at(args.time).do(job)

    # Also run immediately if requested
    if args.run_now:
        job()

    print(f"Scheduler running. Next update at {args.time} daily.")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\nScheduler stopped.")


def cmd_dashboard(args) -> None:
    """Launch the Streamlit dashboard."""
    import subprocess

    dashboard_path = PROJECT_ROOT / "output" / "dashboard.py"

    print("Launching Streamlit dashboard...")
    print("Open http://localhost:8501 in your browser")
    print("Press Ctrl+C to stop.\n")

    try:
        subprocess.run(
            ["streamlit", "run", str(dashboard_path), "--server.port", str(args.port)],
            check=True,
        )
    except FileNotFoundError:
        print("Error: Streamlit not found. Install with: pip install streamlit")
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fantasy Football Ranker - Advanced fantasy football rankings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s demo                        # Run demo with sample data
  %(prog)s demo --position rb          # Show RB rankings only
  %(prog)s demo --cards                # Show top player cards
  %(prog)s scrape                      # Scrape current week data
  %(prog)s rank --format ppr           # Generate PPR rankings
  %(prog)s show                        # Display saved rankings
  %(prog)s schedule --time 06:00       # Set up daily updates
  %(prog)s dashboard                   # Launch web dashboard
        """,
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Demo command (for testing)
    demo_parser = subparsers.add_parser(
        "demo",
        help="Run demo with sample data",
    )
    demo_parser.add_argument(
        "--format",
        choices=["standard", "half_ppr", "ppr", "superflex"],
        default="ppr",
        help="League format (default: ppr)",
    )
    demo_parser.add_argument(
        "--position", "-p",
        choices=["qb", "rb", "wr", "te"],
        help="Show specific position only",
    )
    demo_parser.add_argument(
        "--compare", "-c",
        help="Compare players (comma-separated names)",
    )
    demo_parser.add_argument(
        "--cards",
        action="store_true",
        help="Show detailed player cards for top 3",
    )
    demo_parser.set_defaults(func=cmd_demo)

    # Scrape command
    scrape_parser = subparsers.add_parser(
        "scrape",
        help="Scrape data from all sources",
    )
    scrape_parser.add_argument(
        "--season",
        type=int,
        default=get_current_nfl_season(),
        help="NFL season year (default: current)",
    )
    scrape_parser.add_argument(
        "--week",
        type=int,
        default=None,
        help="Week number (default: current)",
    )
    scrape_parser.set_defaults(func=cmd_scrape)

    # Rank command
    rank_parser = subparsers.add_parser(
        "rank",
        help="Generate player rankings",
    )
    rank_parser.add_argument(
        "--format",
        choices=["standard", "half_ppr", "ppr", "superflex"],
        default="ppr",
        help="League format (default: ppr)",
    )
    rank_parser.add_argument(
        "--season",
        type=int,
        default=get_current_nfl_season(),
        help="NFL season year (default: current)",
    )
    rank_parser.add_argument(
        "--week",
        type=int,
        default=None,
        help="Week number (default: current)",
    )
    rank_parser.set_defaults(func=cmd_rank)

    # Show command
    show_parser = subparsers.add_parser(
        "show",
        help="Display saved rankings",
    )
    show_parser.add_argument(
        "--limit", "-n",
        type=int,
        default=30,
        help="Number of players to show (default: 30)",
    )
    show_parser.set_defaults(func=cmd_show)

    # Schedule command
    schedule_parser = subparsers.add_parser(
        "schedule",
        help="Set up automated daily updates",
    )
    schedule_parser.add_argument(
        "--time",
        default="06:00",
        help="Daily update time (HH:MM format, default: 06:00)",
    )
    schedule_parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run update immediately before starting schedule",
    )
    schedule_parser.set_defaults(func=cmd_schedule)

    # Dashboard command
    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Launch Streamlit web dashboard",
    )
    dashboard_parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Port for dashboard (default: 8501)",
    )
    dashboard_parser.set_defaults(func=cmd_dashboard)

    # Parse arguments
    args = parser.parse_args()

    # Ensure directories exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Set up logging
    setup_logging(getattr(args, 'verbose', False))

    # Initialize database
    init_db()

    # Run command
    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

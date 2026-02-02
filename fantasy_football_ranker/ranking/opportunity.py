"""
Opportunity Metrics Calculator.

Measures player opportunity volume independent of efficiency:
- Target share
- Snap count percentage
- Red zone usage
- Carries/touches
- Air yards share
"""
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class OpportunityMetrics:
    """Container for player opportunity metrics."""
    player_id: int
    name: str
    position: str
    team: str

    # Volume metrics
    snap_percentage: float
    snap_rank: int  # Rank within position

    # Receiving opportunities
    target_share: float  # % of team targets
    targets_per_game: float
    air_yards_share: float
    air_yards_per_target: float

    # Rushing opportunities
    rush_share: float  # % of team rushes
    rushes_per_game: float
    rush_yards_per_game: float

    # High-value opportunities
    red_zone_share: float  # % of team RZ opportunities
    red_zone_targets: int
    red_zone_touches: int
    goal_line_carries: int

    # Composite scores
    opportunity_score: float  # 0-100 overall opportunity rating
    volume_score: float
    quality_score: float  # Quality of opportunities (RZ, goal line)

    def to_dict(self) -> Dict:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "position": self.position,
            "team": self.team,
            "snap_percentage": self.snap_percentage,
            "snap_rank": self.snap_rank,
            "target_share": self.target_share,
            "targets_per_game": self.targets_per_game,
            "air_yards_share": self.air_yards_share,
            "rush_share": self.rush_share,
            "rushes_per_game": self.rushes_per_game,
            "red_zone_share": self.red_zone_share,
            "red_zone_targets": self.red_zone_targets,
            "red_zone_touches": self.red_zone_touches,
            "opportunity_score": self.opportunity_score,
            "volume_score": self.volume_score,
            "quality_score": self.quality_score,
        }


class OpportunityCalculator:
    """
    Calculate opportunity metrics for fantasy football players.

    Opportunity is a key predictor of fantasy success because:
    1. Volume is more stable than efficiency
    2. Targets/touches are controllable by coaching
    3. Opportunity leaders tend to maintain roles
    """

    # Position-specific weights for opportunity components
    POSITION_WEIGHTS = {
        "QB": {
            "snap": 0.3,
            "pass_volume": 0.5,
            "rush": 0.2,
        },
        "RB": {
            "snap": 0.25,
            "targets": 0.30,
            "rush": 0.30,
            "red_zone": 0.15,
        },
        "WR": {
            "snap": 0.20,
            "targets": 0.40,
            "air_yards": 0.25,
            "red_zone": 0.15,
        },
        "TE": {
            "snap": 0.20,
            "targets": 0.40,
            "air_yards": 0.20,
            "red_zone": 0.20,
        },
    }

    def __init__(self):
        """Initialize opportunity calculator."""
        self.team_totals: Dict[str, Dict] = {}

    def calculate_team_totals(
        self,
        players: List[Dict],
    ) -> Dict[str, Dict]:
        """
        Calculate team-level totals for share calculations.

        Args:
            players: List of all player stat dictionaries

        Returns:
            Dictionary of team totals
        """
        team_totals = {}

        for player in players:
            team = player.get("team", "")
            if not team:
                continue

            if team not in team_totals:
                team_totals[team] = {
                    "targets": 0,
                    "rushes": 0,
                    "air_yards": 0,
                    "red_zone_targets": 0,
                    "red_zone_rushes": 0,
                    "pass_attempts": 0,
                }

            team_totals[team]["targets"] += player.get("targets", 0)
            team_totals[team]["rushes"] += player.get("rushing_attempts", 0)
            team_totals[team]["air_yards"] += player.get("air_yards", 0)
            team_totals[team]["red_zone_targets"] += player.get("red_zone_targets", 0)
            team_totals[team]["red_zone_rushes"] += player.get("red_zone_touches", 0)
            team_totals[team]["pass_attempts"] += player.get("passing_attempts", 0)

        self.team_totals = team_totals
        return team_totals

    def calculate_metrics(
        self,
        player: Dict,
        team_totals: Optional[Dict] = None,
    ) -> OpportunityMetrics:
        """
        Calculate opportunity metrics for a single player.

        Args:
            player: Player stats dictionary
            team_totals: Team totals dict (uses cached if not provided)

        Returns:
            OpportunityMetrics object
        """
        team = player.get("team", "")
        totals = (team_totals or self.team_totals).get(team, {})
        games = max(player.get("games_played", 1), 1)

        # Calculate shares
        team_targets = totals.get("targets", 1) or 1
        team_rushes = totals.get("rushes", 1) or 1
        team_air_yards = totals.get("air_yards", 1) or 1
        team_rz = totals.get("red_zone_targets", 1) + totals.get("red_zone_rushes", 1) or 1

        target_share = player.get("targets", 0) / team_targets
        rush_share = player.get("rushing_attempts", 0) / team_rushes
        air_yards_share = player.get("air_yards", 0) / team_air_yards

        rz_targets = player.get("red_zone_targets", 0)
        rz_touches = player.get("red_zone_touches", 0)
        red_zone_share = (rz_targets + rz_touches) / team_rz

        # Per game metrics
        targets_per_game = player.get("targets", 0) / games
        rushes_per_game = player.get("rushing_attempts", 0) / games
        rush_yards_per_game = player.get("rushing_yards", 0) / games

        # Air yards per target
        targets = player.get("targets", 1) or 1
        air_yards_per_target = player.get("air_yards", 0) / targets

        # Calculate composite scores
        position = player.get("position", "RB")
        volume_score = self._calculate_volume_score(player, position, games)
        quality_score = self._calculate_quality_score(player, position, totals)
        opportunity_score = 0.7 * volume_score + 0.3 * quality_score

        return OpportunityMetrics(
            player_id=player.get("player_id", 0),
            name=player.get("name", ""),
            position=position,
            team=team,
            snap_percentage=player.get("snap_percentage", 0),
            snap_rank=0,  # Set later in batch processing
            target_share=round(target_share * 100, 1),
            targets_per_game=round(targets_per_game, 1),
            air_yards_share=round(air_yards_share * 100, 1),
            air_yards_per_target=round(air_yards_per_target, 1),
            rush_share=round(rush_share * 100, 1),
            rushes_per_game=round(rushes_per_game, 1),
            rush_yards_per_game=round(rush_yards_per_game, 1),
            red_zone_share=round(red_zone_share * 100, 1),
            red_zone_targets=rz_targets,
            red_zone_touches=rz_touches,
            goal_line_carries=player.get("goal_line_carries", 0),
            opportunity_score=round(opportunity_score, 1),
            volume_score=round(volume_score, 1),
            quality_score=round(quality_score, 1),
        )

    def _calculate_volume_score(
        self,
        player: Dict,
        position: str,
        games: int,
    ) -> float:
        """
        Calculate volume-based opportunity score.

        Normalized to 0-100 scale based on position benchmarks.
        """
        # Position benchmarks (elite level per game)
        benchmarks = {
            "QB": {"pass_att": 35, "rush_att": 5},
            "RB": {"targets": 6, "rush_att": 18, "snaps": 70},
            "WR": {"targets": 10, "snaps": 90},
            "TE": {"targets": 8, "snaps": 80},
        }

        bench = benchmarks.get(position, benchmarks["RB"])

        if position == "QB":
            pass_att_pg = player.get("passing_attempts", 0) / games
            rush_att_pg = player.get("rushing_attempts", 0) / games
            score = (
                0.8 * min(100, pass_att_pg / bench["pass_att"] * 100) +
                0.2 * min(100, rush_att_pg / bench["rush_att"] * 100)
            )
        elif position == "RB":
            targets_pg = player.get("targets", 0) / games
            rush_pg = player.get("rushing_attempts", 0) / games
            snaps = player.get("snap_percentage", 0)
            score = (
                0.35 * min(100, targets_pg / bench["targets"] * 100) +
                0.40 * min(100, rush_pg / bench["rush_att"] * 100) +
                0.25 * min(100, snaps / bench["snaps"] * 100)
            )
        elif position in ["WR", "TE"]:
            targets_pg = player.get("targets", 0) / games
            snaps = player.get("snap_percentage", 0)
            score = (
                0.65 * min(100, targets_pg / bench["targets"] * 100) +
                0.35 * min(100, snaps / bench["snaps"] * 100)
            )
        else:
            score = 50.0

        return min(100, max(0, score))

    def _calculate_quality_score(
        self,
        player: Dict,
        position: str,
        team_totals: Dict,
    ) -> float:
        """
        Calculate quality of opportunities score.

        Based on red zone usage and high-value touches.
        """
        rz_targets = player.get("red_zone_targets", 0)
        rz_touches = player.get("red_zone_touches", 0)
        total_rz = rz_targets + rz_touches

        # Benchmark: elite players get 30+ RZ opportunities per season
        rz_score = min(100, total_rz / 30 * 100)

        # Air yards quality (for WR/TE)
        if position in ["WR", "TE"]:
            targets = player.get("targets", 1) or 1
            air_yards = player.get("air_yards", 0)
            adot = air_yards / targets  # Average depth of target

            # ADOT of 10+ is good, 15+ is elite
            adot_score = min(100, adot / 12 * 100)

            return 0.6 * rz_score + 0.4 * adot_score

        return rz_score

    def calculate_all(
        self,
        players: List[Dict],
    ) -> Dict[str, List[OpportunityMetrics]]:
        """
        Calculate opportunity metrics for all players by position.

        Args:
            players: List of player stat dictionaries

        Returns:
            Dictionary mapping positions to lists of OpportunityMetrics
        """
        # First calculate team totals
        self.calculate_team_totals(players)

        results = {"QB": [], "RB": [], "WR": [], "TE": []}

        for player in players:
            position = player.get("position", "")
            if position not in results:
                continue

            metrics = self.calculate_metrics(player)
            results[position].append(metrics)

        # Sort by opportunity score and assign ranks
        for position in results:
            results[position].sort(key=lambda x: x.opportunity_score, reverse=True)
            for rank, metrics in enumerate(results[position], 1):
                metrics.snap_rank = rank

        return results


def calculate_workload_sustainability(
    player: Dict,
    historical_workloads: List[Dict],
) -> Dict[str, float]:
    """
    Assess whether current workload is sustainable based on history.

    High workloads can lead to:
    - Injury risk
    - Efficiency decline
    - Committee formation

    Args:
        player: Current player stats
        historical_workloads: Past season workloads

    Returns:
        Sustainability metrics
    """
    current_touches = (
        player.get("rushing_attempts", 0) +
        player.get("receptions", 0)
    )
    games = max(player.get("games_played", 1), 1)
    current_touches_pg = current_touches / games

    # Career average if available
    if historical_workloads:
        career_touches = sum(
            h.get("rushing_attempts", 0) + h.get("receptions", 0)
            for h in historical_workloads
        )
        career_games = sum(h.get("games_played", 1) for h in historical_workloads)
        career_avg = career_touches / max(career_games, 1)
    else:
        career_avg = current_touches_pg

    # Workload deviation
    deviation = (current_touches_pg - career_avg) / max(career_avg, 1)

    # Sustainability score (lower is riskier)
    # High positive deviation = unsustainable increase
    if deviation > 0.3:
        sustainability = 60 - (deviation - 0.3) * 100
    elif deviation < -0.2:
        sustainability = 70  # Reduced role, sustainable but concerning
    else:
        sustainability = 85  # Normal range

    return {
        "touches_per_game": current_touches_pg,
        "career_average": career_avg,
        "workload_deviation": deviation,
        "sustainability_score": max(0, min(100, sustainability)),
        "overworked": deviation > 0.25,
        "underutilized": deviation < -0.25,
    }

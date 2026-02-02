"""
Situational Adjustments Module.

Adjusts player projections based on:
- Strength of Schedule (SOS)
- Expected game script (pace, pass/run ratio)
- Weather conditions
- Home/away splits
- Historical matchup data
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class MatchupAnalysis:
    """Container for matchup analysis results."""
    player_id: int
    name: str
    position: str
    team: str
    opponent: str
    week: int

    # Opponent defense rankings (1 = worst for fantasy, 32 = best)
    opp_rank_vs_position: int
    opp_fantasy_points_allowed: float
    opp_dvoa_rank: int  # Defense-adjusted Value Over Average

    # Game environment
    implied_total: float
    spread: float
    over_under: float
    is_home: bool

    # Adjustments
    matchup_boost: float  # Multiplier (1.0 = neutral)
    game_script_adjustment: float
    pace_adjustment: float

    # Final adjusted projection
    base_projection: float
    adjusted_projection: float
    confidence: float  # 0-100

    def to_dict(self) -> Dict:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "position": self.position,
            "opponent": self.opponent,
            "week": self.week,
            "opp_rank": self.opp_rank_vs_position,
            "implied_total": self.implied_total,
            "spread": self.spread,
            "is_home": self.is_home,
            "matchup_boost": self.matchup_boost,
            "game_script_adj": self.game_script_adjustment,
            "base_projection": self.base_projection,
            "adjusted_projection": self.adjusted_projection,
            "confidence": self.confidence,
        }


@dataclass
class StrengthOfSchedule:
    """Container for strength of schedule analysis."""
    team: str
    position: str
    weeks_analyzed: List[int]

    # Past schedule difficulty
    past_sos_rank: int  # 1 = hardest, 32 = easiest
    past_avg_opp_rank: float

    # Future schedule difficulty
    future_sos_rank: int
    future_avg_opp_rank: float
    remaining_opponents: List[str]

    # Adjustment factors
    past_adjustment: float  # How much past stats were inflated/deflated
    future_adjustment: float  # Expected boost/penalty going forward

    def to_dict(self) -> Dict:
        return {
            "team": self.team,
            "position": self.position,
            "past_sos_rank": self.past_sos_rank,
            "future_sos_rank": self.future_sos_rank,
            "past_adjustment": self.past_adjustment,
            "future_adjustment": self.future_adjustment,
            "remaining_opponents": self.remaining_opponents,
        }


class DefenseRankings:
    """
    Track and calculate defense rankings vs each position.

    Rankings are based on fantasy points allowed to each position.
    """

    def __init__(self):
        """Initialize with empty rankings."""
        self.rankings: Dict[str, Dict[str, float]] = {}
        self.games_played: Dict[str, int] = {}

    def update_from_games(
        self,
        game_results: List[Dict],
    ) -> None:
        """
        Update defense rankings from game results.

        Args:
            game_results: List of game data with fantasy points allowed
        """
        # Aggregate fantasy points allowed by defense
        defense_points = {}

        for game in game_results:
            defense = game.get("defense_team", "")
            position = game.get("position", "")
            points_allowed = game.get("fantasy_points", 0)

            if not defense or not position:
                continue

            key = f"{defense}_{position}"
            if key not in defense_points:
                defense_points[key] = {"total": 0, "games": 0}

            defense_points[key]["total"] += points_allowed
            defense_points[key]["games"] += 1

        # Calculate averages and rankings
        for position in ["QB", "RB", "WR", "TE"]:
            position_data = []

            for team in self._get_all_teams():
                key = f"{team}_{position}"
                if key in defense_points and defense_points[key]["games"] > 0:
                    avg = defense_points[key]["total"] / defense_points[key]["games"]
                    position_data.append((team, avg))

            # Sort by points allowed (descending = more points = worse defense)
            position_data.sort(key=lambda x: x[1], reverse=True)

            if position not in self.rankings:
                self.rankings[position] = {}

            for rank, (team, avg) in enumerate(position_data, 1):
                self.rankings[position][team] = {
                    "rank": rank,
                    "avg_allowed": avg,
                }

    def get_rank(self, team: str, position: str) -> Tuple[int, float]:
        """
        Get defense rank vs position.

        Args:
            team: Team abbreviation
            position: Position

        Returns:
            Tuple of (rank, avg_points_allowed)
        """
        if position in self.rankings and team in self.rankings[position]:
            data = self.rankings[position][team]
            return data["rank"], data["avg_allowed"]
        return 16, 0.0  # Middle of pack default

    def _get_all_teams(self) -> List[str]:
        """Return list of all NFL teams."""
        return [
            "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
            "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
            "LAC", "LAR", "LV", "MIA", "MIN", "NE", "NO", "NYG",
            "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
        ]


class SituationalAdjuster:
    """
    Apply situational adjustments to player projections.

    Factors considered:
    1. Opponent defense ranking vs position
    2. Vegas implied totals and spreads
    3. Expected game script (leading/trailing)
    4. Home/away performance splits
    """

    # Position-specific adjustment factors
    MATCHUP_SENSITIVITY = {
        "QB": 0.08,   # QBs somewhat affected by matchup
        "RB": 0.12,   # RBs more affected by stacked boxes
        "WR": 0.10,   # WRs affected by coverage
        "TE": 0.10,
    }

    # Game script impact by position
    GAME_SCRIPT_SENSITIVITY = {
        "QB": {"leading": 0.95, "trailing": 1.08},  # Pass more when trailing
        "RB": {"leading": 1.10, "trailing": 0.88},  # Run more when leading
        "WR": {"leading": 0.92, "trailing": 1.12},  # More targets when trailing
        "TE": {"leading": 0.95, "trailing": 1.05},
    }

    def __init__(self, defense_rankings: Optional[DefenseRankings] = None):
        """
        Initialize situational adjuster.

        Args:
            defense_rankings: Defense rankings object
        """
        self.defense_rankings = defense_rankings or DefenseRankings()

    def calculate_matchup_boost(
        self,
        position: str,
        opp_rank: int,
    ) -> float:
        """
        Calculate matchup boost based on opponent rank.

        Args:
            position: Player position
            opp_rank: Opponent's rank vs position (1-32)

        Returns:
            Multiplier (>1 = boost, <1 = penalty)
        """
        sensitivity = self.MATCHUP_SENSITIVITY.get(position, 0.10)

        # Normalize rank to -1 to +1 scale
        # Rank 1 (best matchup) = +1, Rank 32 (worst) = -1
        normalized = (33 - 2 * opp_rank) / 31

        # Apply sensitivity
        boost = 1.0 + (normalized * sensitivity)

        return round(boost, 3)

    def calculate_game_script_adjustment(
        self,
        position: str,
        spread: float,
        over_under: float,
    ) -> float:
        """
        Calculate game script adjustment based on Vegas lines.

        Args:
            position: Player position
            spread: Point spread (negative = favored)
            over_under: Game total

        Returns:
            Adjustment multiplier
        """
        sensitivity = self.GAME_SCRIPT_SENSITIVITY.get(
            position,
            {"leading": 1.0, "trailing": 1.0}
        )

        # Determine expected game script
        # Large favorite (spread < -7) = likely leading
        # Large underdog (spread > 7) = likely trailing
        if spread < -7:
            base_adj = sensitivity["leading"]
            intensity = min(1.0, abs(spread) / 14)  # Cap at 14-point spread
        elif spread > 7:
            base_adj = sensitivity["trailing"]
            intensity = min(1.0, spread / 14)
        else:
            base_adj = 1.0
            intensity = 0.0

        # Adjust intensity based on how different from neutral
        adjustment = 1.0 + (base_adj - 1.0) * intensity

        # High totals slightly boost all players
        if over_under > 50:
            adjustment *= 1.02
        elif over_under < 40:
            adjustment *= 0.98

        return round(adjustment, 3)

    def calculate_pace_adjustment(
        self,
        team: str,
        opponent: str,
        team_pace: float,  # Plays per game
        opp_pace: float,
    ) -> float:
        """
        Calculate pace adjustment based on expected plays.

        Args:
            team: Player's team
            opponent: Opposing team
            team_pace: Team's plays per game
            opp_pace: Opponent's plays per game

        Returns:
            Adjustment multiplier
        """
        league_avg_pace = 64.0  # Approximate league average plays per game

        # Expected pace is average of both teams
        expected_pace = (team_pace + opp_pace) / 2

        # Adjustment based on deviation from league average
        pace_deviation = (expected_pace - league_avg_pace) / league_avg_pace

        # Each 5% increase in pace = ~3% more opportunity
        adjustment = 1.0 + (pace_deviation * 0.6)

        return round(adjustment, 3)

    def analyze_matchup(
        self,
        player: Dict,
        opponent: str,
        game_odds: Dict,
        base_projection: float,
    ) -> MatchupAnalysis:
        """
        Perform complete matchup analysis for a player.

        Args:
            player: Player info dictionary
            opponent: Opponent team abbreviation
            game_odds: Game odds dictionary
            base_projection: Base fantasy projection

        Returns:
            MatchupAnalysis object
        """
        position = player.get("position", "RB")
        opp_rank, opp_avg_allowed = self.defense_rankings.get_rank(opponent, position)

        # Get game environment
        spread = game_odds.get("spread", 0)
        over_under = game_odds.get("over_under", 45)
        implied_total = game_odds.get("implied_total", over_under / 2)
        is_home = game_odds.get("is_home", True)

        # Calculate adjustments
        matchup_boost = self.calculate_matchup_boost(position, opp_rank)
        game_script_adj = self.calculate_game_script_adjustment(
            position, spread, over_under
        )
        pace_adj = 1.0  # Would need pace data

        # Home field advantage (small boost)
        home_adj = 1.02 if is_home else 0.98

        # Combine adjustments
        total_adjustment = matchup_boost * game_script_adj * pace_adj * home_adj
        adjusted_projection = base_projection * total_adjustment

        # Confidence based on how extreme the adjustments are
        adj_deviation = abs(total_adjustment - 1.0)
        confidence = max(50, 100 - adj_deviation * 200)

        return MatchupAnalysis(
            player_id=player.get("player_id", 0),
            name=player.get("name", ""),
            position=position,
            team=player.get("team", ""),
            opponent=opponent,
            week=game_odds.get("week", 0),
            opp_rank_vs_position=opp_rank,
            opp_fantasy_points_allowed=opp_avg_allowed,
            opp_dvoa_rank=0,  # Would need DVOA data
            implied_total=implied_total,
            spread=spread,
            over_under=over_under,
            is_home=is_home,
            matchup_boost=matchup_boost,
            game_script_adjustment=game_script_adj,
            pace_adjustment=pace_adj,
            base_projection=base_projection,
            adjusted_projection=round(adjusted_projection, 1),
            confidence=round(confidence, 1),
        )


class ScheduleAnalyzer:
    """Analyze past and future schedule strength."""

    def __init__(self, defense_rankings: DefenseRankings):
        """
        Initialize schedule analyzer.

        Args:
            defense_rankings: Defense rankings object
        """
        self.defense_rankings = defense_rankings

    def analyze_schedule(
        self,
        team: str,
        position: str,
        past_opponents: List[str],
        future_opponents: List[str],
    ) -> StrengthOfSchedule:
        """
        Analyze strength of schedule for a team/position.

        Args:
            team: Team abbreviation
            position: Position to analyze
            past_opponents: List of past opponents
            future_opponents: List of future opponents

        Returns:
            StrengthOfSchedule object
        """
        # Analyze past schedule
        past_ranks = []
        for opp in past_opponents:
            rank, _ = self.defense_rankings.get_rank(opp, position)
            past_ranks.append(rank)

        past_avg = np.mean(past_ranks) if past_ranks else 16

        # Analyze future schedule
        future_ranks = []
        for opp in future_opponents:
            rank, _ = self.defense_rankings.get_rank(opp, position)
            future_ranks.append(rank)

        future_avg = np.mean(future_ranks) if future_ranks else 16

        # Calculate adjustments
        # If past schedule was easy (high ranks), stats are inflated
        # If future schedule is easy, expect boost
        past_adj = 1.0 + (16 - past_avg) / 100  # Slight adjustment
        future_adj = 1.0 + (future_avg - 16) / 100

        return StrengthOfSchedule(
            team=team,
            position=position,
            weeks_analyzed=list(range(1, len(past_opponents) + 1)),
            past_sos_rank=0,  # Would need to rank all teams
            past_avg_opp_rank=round(past_avg, 1),
            future_sos_rank=0,
            future_avg_opp_rank=round(future_avg, 1),
            remaining_opponents=future_opponents,
            past_adjustment=round(past_adj, 3),
            future_adjustment=round(future_adj, 3),
        )

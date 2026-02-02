"""
VORP (Value Over Replacement Player) Calculator.

Calculates how much more value a player provides compared to a
replacement-level player at the same position.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from config.settings import LeagueSettings, RankingConfig, DEFAULT_RANKING


@dataclass
class VORPResult:
    """Container for VORP calculation results."""
    player_id: int
    name: str
    position: str
    fantasy_points: float
    games_played: int
    points_per_game: float
    replacement_level_ppg: float
    vorp: float
    vorp_per_game: float
    position_rank: int
    percentile: float

    def to_dict(self) -> Dict:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "position": self.position,
            "fantasy_points": self.fantasy_points,
            "games_played": self.games_played,
            "points_per_game": self.points_per_game,
            "replacement_level_ppg": self.replacement_level_ppg,
            "vorp": self.vorp,
            "vorp_per_game": self.vorp_per_game,
            "position_rank": self.position_rank,
            "percentile": self.percentile,
        }


class VORPCalculator:
    """
    Calculate Value Over Replacement Player.

    VORP measures how much better a player is compared to a freely available
    replacement-level player (e.g., waiver wire pickup).

    The replacement level is defined as a percentile of players at each position:
    - QB: Top 67% (12 starting QBs in a 12-team league)
    - RB: Top 75% (24 starting RBs)
    - WR: Top 80% (30 starting WRs counting flex)
    - TE: Top 67% (12 starting TEs)
    """

    def __init__(
        self,
        league_settings: Optional[LeagueSettings] = None,
        ranking_config: Optional[RankingConfig] = None,
    ):
        """
        Initialize VORP calculator.

        Args:
            league_settings: League configuration
            ranking_config: Ranking algorithm configuration
        """
        self.league_settings = league_settings
        self.ranking_config = ranking_config or DEFAULT_RANKING

        # Calculate replacement level thresholds based on league settings
        self.replacement_levels = self._calculate_replacement_levels()

    def _calculate_replacement_levels(self) -> Dict[str, int]:
        """
        Calculate the number of players at each position that are
        above replacement level.

        Based on typical 12-team league rosters.
        """
        # Default replacement levels (number of startable players)
        # These represent approximately the Nth best player at each position
        # that would be available on waivers
        base_levels = {
            "QB": 12,   # 1 starter per team
            "RB": 24,   # 2 starters per team (before flex)
            "WR": 30,   # 2-3 starters per team (including flex)
            "TE": 12,   # 1 starter per team
            "K": 12,
            "DST": 12,
        }

        if self.league_settings:
            # Adjust based on actual league settings
            num_teams = 12  # Assume 12 teams, could be configurable
            base_levels["QB"] = num_teams * self.league_settings.starting_qb
            base_levels["RB"] = num_teams * self.league_settings.starting_rb
            base_levels["WR"] = num_teams * self.league_settings.starting_wr
            base_levels["TE"] = num_teams * self.league_settings.starting_te
            # Account for flex positions (assume 50% RB, 50% WR)
            flex_slots = num_teams * self.league_settings.starting_flex
            base_levels["RB"] += int(flex_slots * 0.4)
            base_levels["WR"] += int(flex_slots * 0.5)
            base_levels["TE"] += int(flex_slots * 0.1)

        return base_levels

    def calculate_replacement_level(
        self,
        position: str,
        player_points: List[float],
    ) -> float:
        """
        Calculate the replacement level points per game for a position.

        Args:
            position: Position (QB, RB, WR, TE)
            player_points: List of fantasy points per game for all players

        Returns:
            Replacement level PPG
        """
        if not player_points:
            return 0.0

        # Sort descending
        sorted_points = sorted(player_points, reverse=True)

        # Get replacement level threshold
        replacement_rank = self.replacement_levels.get(position, 12)

        # The replacement player is the one just below the threshold
        if replacement_rank < len(sorted_points):
            return sorted_points[replacement_rank]
        elif len(sorted_points) > 0:
            return sorted_points[-1]  # Use worst player if not enough data
        return 0.0

    def calculate_vorp(
        self,
        players: List[Dict],
        position: str,
        games_threshold: int = 3,
    ) -> List[VORPResult]:
        """
        Calculate VORP for all players at a position.

        Args:
            players: List of player dictionaries with stats
            position: Position to calculate VORP for
            games_threshold: Minimum games played to be included

        Returns:
            List of VORPResult objects sorted by VORP descending
        """
        # Filter to position and minimum games
        position_players = [
            p for p in players
            if p.get("position") == position and p.get("games_played", 0) >= games_threshold
        ]

        if not position_players:
            return []

        # Calculate PPG for each player
        for player in position_players:
            games = player.get("games_played", 1)
            points = player.get("fantasy_points", 0)
            player["ppg"] = points / max(games, 1)

        # Get replacement level
        all_ppg = [p["ppg"] for p in position_players]
        replacement_ppg = self.calculate_replacement_level(position, all_ppg)

        # Calculate VORP for each player
        results = []
        sorted_players = sorted(position_players, key=lambda x: x["ppg"], reverse=True)

        for rank, player in enumerate(sorted_players, 1):
            ppg = player["ppg"]
            games = player.get("games_played", 0)
            total_points = player.get("fantasy_points", 0)

            # VORP = (Player PPG - Replacement PPG) * Games Played
            vorp_per_game = ppg - replacement_ppg
            vorp_total = vorp_per_game * games

            # Calculate percentile
            percentile = 1.0 - (rank - 1) / max(len(sorted_players), 1)

            result = VORPResult(
                player_id=player.get("player_id", 0),
                name=player.get("name", ""),
                position=position,
                fantasy_points=total_points,
                games_played=games,
                points_per_game=ppg,
                replacement_level_ppg=replacement_ppg,
                vorp=vorp_total,
                vorp_per_game=vorp_per_game,
                position_rank=rank,
                percentile=percentile,
            )
            results.append(result)

        return results

    def calculate_all_positions(
        self,
        players: List[Dict],
        games_threshold: int = 3,
    ) -> Dict[str, List[VORPResult]]:
        """
        Calculate VORP for all fantasy-relevant positions.

        Args:
            players: List of all player dictionaries
            games_threshold: Minimum games to be included

        Returns:
            Dictionary mapping positions to VORP results
        """
        positions = ["QB", "RB", "WR", "TE"]
        results = {}

        for pos in positions:
            results[pos] = self.calculate_vorp(players, pos, games_threshold)

        return results

    def normalize_vorp_score(
        self,
        vorp: float,
        position: str,
        all_vorp_values: List[float],
    ) -> float:
        """
        Normalize VORP to a 0-100 scale for cross-position comparison.

        Uses z-score normalization then maps to 0-100.

        Args:
            vorp: Player's VORP value
            position: Player's position
            all_vorp_values: All VORP values at the position

        Returns:
            Normalized score (0-100)
        """
        if not all_vorp_values:
            return 50.0

        mean_vorp = np.mean(all_vorp_values)
        std_vorp = np.std(all_vorp_values)

        if std_vorp == 0:
            return 50.0

        # Z-score
        z = (vorp - mean_vorp) / std_vorp

        # Map z-score to 0-100 (z of -3 to +3 maps to 0-100)
        normalized = 50 + (z * 16.67)

        # Clamp to valid range
        return max(0, min(100, normalized))


def calculate_positional_scarcity(
    vorp_results: Dict[str, List[VORPResult]],
) -> Dict[str, float]:
    """
    Calculate positional scarcity based on VORP distribution.

    Higher scarcity means the position has more top-heavy value,
    making elite players more valuable.

    Args:
        vorp_results: VORP results for all positions

    Returns:
        Dictionary mapping positions to scarcity scores (0-1)
    """
    scarcity = {}

    for position, results in vorp_results.items():
        if not results or len(results) < 5:
            scarcity[position] = 0.5
            continue

        # Get VORP values
        vorps = [r.vorp for r in results if r.vorp > 0]

        if not vorps:
            scarcity[position] = 0.5
            continue

        # Calculate Gini coefficient as measure of inequality
        # Higher Gini = more top-heavy = more scarce position
        sorted_vorps = sorted(vorps)
        n = len(sorted_vorps)
        cumsum = np.cumsum(sorted_vorps)
        gini = (2 * np.sum((np.arange(1, n + 1) * sorted_vorps))) / (n * np.sum(sorted_vorps)) - (n + 1) / n

        # Normalize Gini to 0-1 range (typical range is 0.3-0.6)
        scarcity[position] = max(0, min(1, (gini - 0.2) / 0.5))

    return scarcity

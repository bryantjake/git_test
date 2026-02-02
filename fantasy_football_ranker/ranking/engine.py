"""
Composite Ranking Engine.

Combines all ranking components into final player rankings:
- VORP scores
- Bayesian projections
- Opportunity metrics
- Situational adjustments
- Risk assessment
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from .vorp import VORPCalculator, VORPResult
from .bayesian import BayesianUpdater, BayesianEstimate
from .opportunity import OpportunityCalculator, OpportunityMetrics
from .situational import SituationalAdjuster, MatchupAnalysis
from .risk import RiskCalculator, RiskAssessment

from config.settings import LeagueSettings, RankingConfig, DEFAULT_RANKING


@dataclass
class PlayerRanking:
    """Complete ranking for a single player."""
    player_id: int
    name: str
    team: str
    position: str

    # Final rankings
    overall_rank: int
    position_rank: int
    tier: int

    # Component scores (0-100 scale)
    vorp_score: float
    bayesian_score: float
    opportunity_score: float
    matchup_score: float
    risk_score: float  # Lower is better (inverted for final calc)

    # Composite score
    composite_score: float

    # Key metrics
    projected_points: float
    floor: float
    ceiling: float
    confidence: float

    # Trend indicators
    trending: str  # "up", "down", "stable"
    hot_streak: bool
    injury_status: str

    # Detailed breakdowns (optional)
    vorp_detail: Optional[VORPResult] = None
    bayesian_detail: Optional[BayesianEstimate] = None
    opportunity_detail: Optional[OpportunityMetrics] = None
    risk_detail: Optional[RiskAssessment] = None

    def to_dict(self) -> Dict:
        return {
            "rank": self.overall_rank,
            "position_rank": self.position_rank,
            "tier": self.tier,
            "name": self.name,
            "team": self.team,
            "position": self.position,
            "projected_points": self.projected_points,
            "composite_score": self.composite_score,
            "vorp_score": self.vorp_score,
            "opportunity_score": self.opportunity_score,
            "risk_score": self.risk_score,
            "floor": self.floor,
            "ceiling": self.ceiling,
            "trending": self.trending,
            "injury_status": self.injury_status,
        }


@dataclass
class RankingResults:
    """Container for complete ranking results."""
    season: int
    week: int
    league_format: str
    generated_at: str

    # Rankings by category
    overall_rankings: List[PlayerRanking]
    qb_rankings: List[PlayerRanking]
    rb_rankings: List[PlayerRanking]
    wr_rankings: List[PlayerRanking]
    te_rankings: List[PlayerRanking]

    # Tiers
    tiers: Dict[str, List[List[PlayerRanking]]]

    # Summary stats
    total_players: int

    def get_position_rankings(self, position: str) -> List[PlayerRanking]:
        """Get rankings for a specific position."""
        position_map = {
            "QB": self.qb_rankings,
            "RB": self.rb_rankings,
            "WR": self.wr_rankings,
            "TE": self.te_rankings,
        }
        return position_map.get(position.upper(), [])


class RankingEngine:
    """
    Main ranking engine that orchestrates all components.

    Combines VORP, Bayesian projections, opportunity metrics,
    situational factors, and risk assessment into final rankings.
    """

    # Default component weights
    DEFAULT_WEIGHTS = {
        "vorp": 0.25,
        "bayesian": 0.25,
        "opportunity": 0.20,
        "matchup": 0.15,
        "risk": 0.15,  # Inverted - lower risk = higher score
    }

    def __init__(
        self,
        league_settings: Optional[LeagueSettings] = None,
        ranking_config: Optional[RankingConfig] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize ranking engine.

        Args:
            league_settings: League configuration
            ranking_config: Ranking algorithm configuration
            weights: Custom component weights
        """
        self.league_settings = league_settings
        self.ranking_config = ranking_config or DEFAULT_RANKING
        self.weights = weights or self.DEFAULT_WEIGHTS

        # Initialize components
        self.vorp_calculator = VORPCalculator(league_settings, ranking_config)
        self.bayesian_updater = BayesianUpdater()
        self.opportunity_calculator = OpportunityCalculator()
        self.situational_adjuster = SituationalAdjuster()
        self.risk_calculator = RiskCalculator()

    def generate_rankings(
        self,
        players: List[Dict],
        weekly_scores: Dict[int, List[float]],
        projections: Dict[int, float],
        injury_history: Dict[int, List[Dict]],
        game_odds: Dict[str, Dict],
        current_week: int,
        season: int,
    ) -> RankingResults:
        """
        Generate complete rankings for all players.

        Args:
            players: List of player stat dictionaries
            weekly_scores: Map of player_id to weekly scores
            projections: Map of player_id to season projections
            injury_history: Map of player_id to injury history
            game_odds: Map of team to game odds
            current_week: Current NFL week
            season: NFL season year

        Returns:
            RankingResults object
        """
        from datetime import datetime

        # Step 1: Calculate VORP for all positions
        vorp_results = self.vorp_calculator.calculate_all_positions(players)

        # Step 2: Calculate Bayesian estimates
        bayesian_results = self._calculate_bayesian(
            players, weekly_scores, projections, current_week
        )

        # Step 3: Calculate opportunity metrics
        opportunity_results = self.opportunity_calculator.calculate_all(players)

        # Step 4: Calculate risk assessments
        risk_results = self._calculate_risk(players, weekly_scores, injury_history)

        # Step 5: Combine into player rankings
        all_rankings = self._combine_rankings(
            players=players,
            vorp_results=vorp_results,
            bayesian_results=bayesian_results,
            opportunity_results=opportunity_results,
            risk_results=risk_results,
            game_odds=game_odds,
        )

        # Step 6: Sort and assign ranks
        all_rankings.sort(key=lambda x: x.composite_score, reverse=True)
        for i, ranking in enumerate(all_rankings, 1):
            ranking.overall_rank = i

        # Separate by position and assign position ranks
        position_rankings = self._separate_by_position(all_rankings)

        # Calculate tiers
        tiers = self._calculate_tiers(position_rankings)

        return RankingResults(
            season=season,
            week=current_week,
            league_format=self.league_settings.name if self.league_settings else "ppr",
            generated_at=datetime.utcnow().isoformat(),
            overall_rankings=all_rankings,
            qb_rankings=position_rankings.get("QB", []),
            rb_rankings=position_rankings.get("RB", []),
            wr_rankings=position_rankings.get("WR", []),
            te_rankings=position_rankings.get("TE", []),
            tiers=tiers,
            total_players=len(all_rankings),
        )

    def _calculate_bayesian(
        self,
        players: List[Dict],
        weekly_scores: Dict[int, List[float]],
        projections: Dict[int, float],
        current_week: int,
    ) -> Dict[int, BayesianEstimate]:
        """Calculate Bayesian estimates for all players."""
        estimates = self.bayesian_updater.batch_update(
            players=players,
            weekly_scores=weekly_scores,
            projections=projections,
            current_week=current_week,
        )
        return {e.player_id: e for e in estimates}

    def _calculate_risk(
        self,
        players: List[Dict],
        weekly_scores: Dict[int, List[float]],
        injury_history: Dict[int, List[Dict]],
    ) -> Dict[int, RiskAssessment]:
        """Calculate risk assessments for all players."""
        results = {}
        for player in players:
            player_id = player.get("player_id", 0)
            scores = weekly_scores.get(player_id, [])
            injuries = injury_history.get(player_id, [])

            assessment = self.risk_calculator.assess_player(
                player=player,
                weekly_scores=scores,
                injury_history=injuries,
            )
            results[player_id] = assessment

        return results

    def _combine_rankings(
        self,
        players: List[Dict],
        vorp_results: Dict[str, List[VORPResult]],
        bayesian_results: Dict[int, BayesianEstimate],
        opportunity_results: Dict[str, List[OpportunityMetrics]],
        risk_results: Dict[int, RiskAssessment],
        game_odds: Dict[str, Dict],
    ) -> List[PlayerRanking]:
        """Combine all component scores into final rankings."""
        rankings = []

        # Create lookup dicts
        vorp_lookup = {}
        for pos, results in vorp_results.items():
            for r in results:
                vorp_lookup[r.player_id] = r

        opp_lookup = {}
        for pos, results in opportunity_results.items():
            for r in results:
                opp_lookup[r.player_id] = r

        for player in players:
            player_id = player.get("player_id", 0)
            position = player.get("position", "")

            if position not in ["QB", "RB", "WR", "TE"]:
                continue

            # Get component results
            vorp = vorp_lookup.get(player_id)
            bayesian = bayesian_results.get(player_id)
            opportunity = opp_lookup.get(player_id)
            risk = risk_results.get(player_id)

            # Calculate component scores (0-100 scale)
            vorp_score = self._normalize_vorp(vorp) if vorp else 50.0
            bayesian_score = self._normalize_bayesian(bayesian) if bayesian else 50.0
            opp_score = opportunity.opportunity_score if opportunity else 50.0
            risk_score = risk.overall_risk_score if risk else 50.0

            # Matchup score (would need to look up opponent)
            team = player.get("team", "")
            matchup_score = 50.0  # Default neutral
            if team in game_odds:
                # Simple matchup boost based on implied total
                implied = game_odds[team].get("implied_total", 22)
                matchup_score = min(100, max(0, (implied - 15) * 5))

            # Calculate composite score
            # Invert risk score (lower risk = higher contribution)
            inverted_risk = 100 - risk_score

            composite = (
                vorp_score * self.weights["vorp"] +
                bayesian_score * self.weights["bayesian"] +
                opp_score * self.weights["opportunity"] +
                matchup_score * self.weights["matchup"] +
                inverted_risk * self.weights["risk"]
            )

            # Get floor/ceiling from risk assessment
            floor = risk.floor if risk else 0.0
            ceiling = risk.ceiling if risk else 0.0

            # Projected points from Bayesian
            projected = bayesian.posterior_mean if bayesian else player.get("ppg", 0)

            # Trending info
            trending = bayesian.trending if bayesian else "stable"
            hot_streak = False  # Would come from trend analysis

            ranking = PlayerRanking(
                player_id=player_id,
                name=player.get("name", ""),
                team=team,
                position=position,
                overall_rank=0,  # Set later
                position_rank=0,  # Set later
                tier=0,  # Set later
                vorp_score=round(vorp_score, 1),
                bayesian_score=round(bayesian_score, 1),
                opportunity_score=round(opp_score, 1),
                matchup_score=round(matchup_score, 1),
                risk_score=round(risk_score, 1),
                composite_score=round(composite, 1),
                projected_points=round(projected, 1),
                floor=floor,
                ceiling=ceiling,
                confidence=bayesian.confidence_score if bayesian else 50.0,
                trending=trending,
                hot_streak=hot_streak,
                injury_status=player.get("injury_status", "Healthy"),
                vorp_detail=vorp,
                bayesian_detail=bayesian,
                opportunity_detail=opportunity,
                risk_detail=risk,
            )
            rankings.append(ranking)

        return rankings

    def _normalize_vorp(self, vorp: VORPResult) -> float:
        """Normalize VORP to 0-100 scale."""
        # Use percentile
        return vorp.percentile * 100

    def _normalize_bayesian(self, bayesian: BayesianEstimate) -> float:
        """Normalize Bayesian posterior to 0-100 scale."""
        # Scale based on typical PPG ranges
        ppg = bayesian.posterior_mean

        # Position-specific scaling
        max_ppg = {
            "QB": 25,
            "RB": 20,
            "WR": 18,
            "TE": 15,
        }.get(bayesian.position, 18)

        return min(100, max(0, (ppg / max_ppg) * 100))

    def _separate_by_position(
        self,
        rankings: List[PlayerRanking],
    ) -> Dict[str, List[PlayerRanking]]:
        """Separate rankings by position and assign position ranks."""
        position_rankings = {
            "QB": [],
            "RB": [],
            "WR": [],
            "TE": [],
        }

        for ranking in rankings:
            if ranking.position in position_rankings:
                position_rankings[ranking.position].append(ranking)

        # Sort each position and assign ranks
        for position, pos_rankings in position_rankings.items():
            pos_rankings.sort(key=lambda x: x.composite_score, reverse=True)
            for i, ranking in enumerate(pos_rankings, 1):
                ranking.position_rank = i

        return position_rankings

    def _calculate_tiers(
        self,
        position_rankings: Dict[str, List[PlayerRanking]],
        num_tiers: int = 6,
    ) -> Dict[str, List[List[PlayerRanking]]]:
        """
        Calculate tiers for each position using score gaps.

        Players with similar scores are grouped together.
        """
        tiers = {}

        for position, rankings in position_rankings.items():
            if not rankings:
                tiers[position] = []
                continue

            # Use k-means-like approach to find natural breaks
            scores = [r.composite_score for r in rankings]

            # Simple tier breaks based on score distribution
            if len(scores) < num_tiers:
                # Not enough players for full tiers
                tiers[position] = [[r] for r in rankings]
                for i, tier in enumerate(tiers[position], 1):
                    for r in tier:
                        r.tier = i
                continue

            # Calculate tier boundaries
            min_score = min(scores)
            max_score = max(scores)
            score_range = max_score - min_score

            if score_range == 0:
                tiers[position] = [rankings]
                for r in rankings:
                    r.tier = 1
                continue

            # Create tiers based on score ranges
            tier_size = score_range / num_tiers
            position_tiers = [[] for _ in range(num_tiers)]

            for ranking in rankings:
                tier_idx = min(
                    num_tiers - 1,
                    int((max_score - ranking.composite_score) / tier_size)
                )
                position_tiers[tier_idx].append(ranking)
                ranking.tier = tier_idx + 1

            # Remove empty tiers
            tiers[position] = [t for t in position_tiers if t]

        return tiers


def quick_rank(
    players: List[Dict],
    format: str = "ppr",
) -> List[PlayerRanking]:
    """
    Quick ranking function for simple use cases.

    Args:
        players: List of player dictionaries with stats
        format: League format (standard, half_ppr, ppr)

    Returns:
        List of PlayerRanking objects sorted by rank
    """
    from config.settings import LEAGUE_PRESETS

    league_settings = LEAGUE_PRESETS.get(format)
    engine = RankingEngine(league_settings=league_settings)

    # Simple ranking without detailed data
    results = engine.generate_rankings(
        players=players,
        weekly_scores={},
        projections={p.get("player_id", 0): p.get("ppg", 10) for p in players},
        injury_history={},
        game_odds={},
        current_week=1,
        season=2024,
    )

    return results.overall_rankings

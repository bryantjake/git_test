"""
Bayesian Updating Module for Fantasy Football Rankings.

Combines preseason priors (projections, ADP) with in-season performance
using Bayesian inference to produce updated player projections.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from scipy import stats


@dataclass
class BayesianEstimate:
    """Container for Bayesian estimation results."""
    player_id: int
    name: str
    position: str

    # Prior (preseason expectations)
    prior_mean: float
    prior_std: float

    # Likelihood (observed performance)
    observed_mean: float
    observed_std: float
    sample_size: int  # Games played

    # Posterior (updated belief)
    posterior_mean: float
    posterior_std: float

    # Confidence metrics
    credible_interval_low: float  # 90% CI
    credible_interval_high: float
    confidence_score: float  # 0-100, higher = more certain

    # Change metrics
    change_from_prior: float
    trending: str  # "up", "down", "stable"

    def to_dict(self) -> Dict:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "position": self.position,
            "prior_mean": self.prior_mean,
            "prior_std": self.prior_std,
            "observed_mean": self.observed_mean,
            "observed_std": self.observed_std,
            "games_played": self.sample_size,
            "posterior_mean": self.posterior_mean,
            "posterior_std": self.posterior_std,
            "ci_low": self.credible_interval_low,
            "ci_high": self.credible_interval_high,
            "confidence": self.confidence_score,
            "change_from_prior": self.change_from_prior,
            "trending": self.trending,
        }


class BayesianUpdater:
    """
    Bayesian updating for fantasy football projections.

    Uses conjugate prior approach:
    - Prior: Normal distribution based on preseason projections
    - Likelihood: Normal distribution of observed game performances
    - Posterior: Updated Normal distribution

    The weight given to prior vs observed data changes throughout the season:
    - Early season (weeks 1-4): Prior weight 70%
    - Mid season (weeks 5-10): Prior weight 40%
    - Late season (weeks 11+): Prior weight 20%
    """

    # Default prior standard deviations by position (PPG)
    DEFAULT_PRIOR_STD = {
        "QB": 6.0,
        "RB": 5.0,
        "WR": 4.5,
        "TE": 3.5,
        "K": 2.5,
        "DST": 3.0,
    }

    def __init__(
        self,
        prior_weight_early: float = 0.7,
        prior_weight_mid: float = 0.4,
        prior_weight_late: float = 0.2,
    ):
        """
        Initialize Bayesian updater.

        Args:
            prior_weight_early: Prior weight for weeks 1-4
            prior_weight_mid: Prior weight for weeks 5-10
            prior_weight_late: Prior weight for weeks 11+
        """
        self.prior_weights = {
            "early": prior_weight_early,
            "mid": prior_weight_mid,
            "late": prior_weight_late,
        }

    def get_season_phase(self, week: int) -> str:
        """Determine season phase based on week number."""
        if week <= 4:
            return "early"
        elif week <= 10:
            return "mid"
        else:
            return "late"

    def get_prior_weight(self, week: int, games_played: int) -> float:
        """
        Calculate prior weight based on week and sample size.

        Args:
            week: Current NFL week
            games_played: Number of games the player has played

        Returns:
            Weight for prior (0-1)
        """
        phase = self.get_season_phase(week)
        base_weight = self.prior_weights[phase]

        # Adjust for sample size - more games = less prior weight
        sample_adjustment = max(0, 1 - (games_played / 17))

        # Combine phase weight with sample adjustment
        return base_weight * sample_adjustment + (1 - sample_adjustment) * 0.1

    def update(
        self,
        prior_mean: float,
        prior_std: float,
        observations: List[float],
        current_week: int,
    ) -> Tuple[float, float]:
        """
        Perform Bayesian update to get posterior distribution.

        Uses conjugate normal-normal model with known variance.

        Args:
            prior_mean: Prior expected PPG
            prior_std: Prior standard deviation
            observations: List of observed game scores
            current_week: Current NFL week

        Returns:
            Tuple of (posterior_mean, posterior_std)
        """
        if not observations:
            return prior_mean, prior_std

        n = len(observations)
        obs_mean = np.mean(observations)
        obs_std = np.std(observations) if n > 1 else prior_std

        # Get weight for prior based on season phase
        prior_weight = self.get_prior_weight(current_week, n)

        # Precision-weighted combination (conjugate update)
        prior_precision = 1 / (prior_std ** 2)
        obs_precision = n / (obs_std ** 2) if obs_std > 0 else 0

        # Apply weighting
        weighted_prior_precision = prior_precision * prior_weight
        weighted_obs_precision = obs_precision * (1 - prior_weight)

        total_precision = weighted_prior_precision + weighted_obs_precision

        if total_precision == 0:
            return prior_mean, prior_std

        # Posterior parameters
        posterior_mean = (
            weighted_prior_precision * prior_mean +
            weighted_obs_precision * obs_mean
        ) / total_precision

        posterior_std = np.sqrt(1 / total_precision)

        return posterior_mean, posterior_std

    def calculate_estimate(
        self,
        player: Dict,
        weekly_scores: List[float],
        projection: float,
        current_week: int,
    ) -> BayesianEstimate:
        """
        Calculate full Bayesian estimate for a player.

        Args:
            player: Player info dictionary
            weekly_scores: List of weekly fantasy scores
            projection: Preseason projection (PPG)
            current_week: Current NFL week

        Returns:
            BayesianEstimate object
        """
        position = player.get("position", "RB")
        prior_std = self.DEFAULT_PRIOR_STD.get(position, 5.0)

        # Calculate observed stats
        n = len(weekly_scores)
        obs_mean = np.mean(weekly_scores) if n > 0 else projection
        obs_std = np.std(weekly_scores) if n > 1 else prior_std

        # Bayesian update
        posterior_mean, posterior_std = self.update(
            prior_mean=projection,
            prior_std=prior_std,
            observations=weekly_scores,
            current_week=current_week,
        )

        # Calculate 90% credible interval
        ci_low = posterior_mean - 1.645 * posterior_std
        ci_high = posterior_mean + 1.645 * posterior_std

        # Confidence score (inverse of uncertainty, normalized)
        max_std = prior_std * 2  # Maximum expected uncertainty
        confidence = max(0, min(100, 100 * (1 - posterior_std / max_std)))

        # Change from prior
        change = posterior_mean - projection

        # Determine trend
        if change > 2:
            trending = "up"
        elif change < -2:
            trending = "down"
        else:
            trending = "stable"

        return BayesianEstimate(
            player_id=player.get("player_id", 0),
            name=player.get("name", ""),
            position=position,
            prior_mean=projection,
            prior_std=prior_std,
            observed_mean=obs_mean,
            observed_std=obs_std,
            sample_size=n,
            posterior_mean=posterior_mean,
            posterior_std=posterior_std,
            credible_interval_low=max(0, ci_low),
            credible_interval_high=ci_high,
            confidence_score=confidence,
            change_from_prior=change,
            trending=trending,
        )

    def batch_update(
        self,
        players: List[Dict],
        weekly_scores: Dict[int, List[float]],
        projections: Dict[int, float],
        current_week: int,
    ) -> List[BayesianEstimate]:
        """
        Calculate Bayesian estimates for multiple players.

        Args:
            players: List of player dictionaries
            weekly_scores: Dict mapping player_id to list of scores
            projections: Dict mapping player_id to projection
            current_week: Current NFL week

        Returns:
            List of BayesianEstimate objects
        """
        estimates = []

        for player in players:
            player_id = player.get("player_id", 0)
            scores = weekly_scores.get(player_id, [])
            projection = projections.get(player_id, 10.0)  # Default projection

            estimate = self.calculate_estimate(
                player=player,
                weekly_scores=scores,
                projection=projection,
                current_week=current_week,
            )
            estimates.append(estimate)

        return estimates


class TrendAnalyzer:
    """Analyze player performance trends using rolling windows."""

    def __init__(self, window_size: int = 3):
        """
        Initialize trend analyzer.

        Args:
            window_size: Number of recent games to analyze for trends
        """
        self.window_size = window_size

    def calculate_trend(
        self,
        scores: List[float],
    ) -> Dict[str, float]:
        """
        Calculate trend metrics from game scores.

        Args:
            scores: List of game scores (oldest to newest)

        Returns:
            Dictionary of trend metrics
        """
        if len(scores) < 2:
            return {
                "trend_slope": 0.0,
                "recent_avg": scores[0] if scores else 0.0,
                "season_avg": scores[0] if scores else 0.0,
                "hot_streak": False,
                "cold_streak": False,
            }

        # Linear regression for trend
        x = np.arange(len(scores))
        slope, intercept = np.polyfit(x, scores, 1)

        # Recent vs season average
        recent = scores[-self.window_size:] if len(scores) >= self.window_size else scores
        recent_avg = np.mean(recent)
        season_avg = np.mean(scores)

        # Streak detection
        hot_streak = all(s > season_avg for s in recent) and len(recent) >= 2
        cold_streak = all(s < season_avg for s in recent) and len(recent) >= 2

        return {
            "trend_slope": slope,
            "recent_avg": recent_avg,
            "season_avg": season_avg,
            "hot_streak": hot_streak,
            "cold_streak": cold_streak,
            "momentum": recent_avg - season_avg,
        }

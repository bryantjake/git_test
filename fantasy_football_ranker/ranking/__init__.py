"""
Ranking module for Fantasy Football Ranker.

Components:
- VORP (Value Over Replacement Player) calculation
- Bayesian updating with preseason priors
- Opportunity metrics (target share, snap counts, red zone usage)
- Situational adjustments (strength of schedule, game script)
- Risk assessment (injury history, volatility)
"""
from .vorp import VORPCalculator, VORPResult, calculate_positional_scarcity
from .bayesian import BayesianUpdater, BayesianEstimate, TrendAnalyzer
from .opportunity import OpportunityCalculator, OpportunityMetrics
from .situational import (
    SituationalAdjuster,
    MatchupAnalysis,
    ScheduleAnalyzer,
    StrengthOfSchedule,
    DefenseRankings,
)
from .risk import RiskCalculator, RiskAssessment
from .engine import RankingEngine, PlayerRanking, RankingResults, quick_rank

__all__ = [
    # VORP
    "VORPCalculator",
    "VORPResult",
    "calculate_positional_scarcity",
    # Bayesian
    "BayesianUpdater",
    "BayesianEstimate",
    "TrendAnalyzer",
    # Opportunity
    "OpportunityCalculator",
    "OpportunityMetrics",
    # Situational
    "SituationalAdjuster",
    "MatchupAnalysis",
    "ScheduleAnalyzer",
    "StrengthOfSchedule",
    "DefenseRankings",
    # Risk
    "RiskCalculator",
    "RiskAssessment",
    # Engine
    "RankingEngine",
    "PlayerRanking",
    "RankingResults",
    "quick_rank",
]

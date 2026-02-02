"""
Risk Assessment Module.

Evaluates player risk factors:
- Injury history and current status
- Performance volatility/consistency
- Age-related decline risk
- Workload sustainability
- Situation stability (depth chart, team changes)
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RiskAssessment:
    """Container for player risk assessment."""
    player_id: int
    name: str
    position: str

    # Overall risk score (0-100, higher = riskier)
    overall_risk_score: float

    # Component scores
    injury_risk: float
    volatility_risk: float
    age_risk: float
    workload_risk: float
    situation_risk: float

    # Risk factors breakdown
    injury_history: List[str]
    current_injury_status: str
    games_missed_last_3_years: int
    coefficient_of_variation: float  # Consistency metric
    age: int
    years_experience: int

    # Risk tier
    risk_tier: str  # "low", "medium", "high", "very_high"

    # Boom/bust profile
    boom_rate: float  # % of games above 1.5x average
    bust_rate: float  # % of games below 0.5x average
    floor: float
    ceiling: float

    def to_dict(self) -> Dict:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "position": self.position,
            "overall_risk": self.overall_risk_score,
            "injury_risk": self.injury_risk,
            "volatility_risk": self.volatility_risk,
            "age_risk": self.age_risk,
            "workload_risk": self.workload_risk,
            "situation_risk": self.situation_risk,
            "risk_tier": self.risk_tier,
            "boom_rate": self.boom_rate,
            "bust_rate": self.bust_rate,
            "floor": self.floor,
            "ceiling": self.ceiling,
        }


class RiskCalculator:
    """
    Calculate comprehensive risk scores for fantasy players.

    Risk factors are weighted by position since different positions
    have different risk profiles (e.g., RBs have highest injury risk).
    """

    # Position-specific risk weights
    RISK_WEIGHTS = {
        "QB": {
            "injury": 0.20,
            "volatility": 0.25,
            "age": 0.15,
            "workload": 0.15,
            "situation": 0.25,
        },
        "RB": {
            "injury": 0.30,
            "volatility": 0.20,
            "age": 0.20,
            "workload": 0.20,
            "situation": 0.10,
        },
        "WR": {
            "injury": 0.20,
            "volatility": 0.25,
            "age": 0.15,
            "workload": 0.10,
            "situation": 0.30,
        },
        "TE": {
            "injury": 0.25,
            "volatility": 0.20,
            "age": 0.15,
            "workload": 0.10,
            "situation": 0.30,
        },
    }

    # Age thresholds for decline risk
    AGE_THRESHOLDS = {
        "QB": {"prime_end": 36, "cliff": 40},
        "RB": {"prime_end": 27, "cliff": 30},
        "WR": {"prime_end": 30, "cliff": 33},
        "TE": {"prime_end": 30, "cliff": 33},
    }

    def __init__(self):
        """Initialize risk calculator."""
        pass

    def calculate_injury_risk(
        self,
        injury_history: List[Dict],
        current_status: str,
        games_played_recent: int,
        possible_games: int = 17,
    ) -> Tuple[float, List[str]]:
        """
        Calculate injury risk score.

        Args:
            injury_history: List of historical injury dictionaries
            current_status: Current injury status
            games_played_recent: Games played in recent seasons
            possible_games: Maximum possible games

        Returns:
            Tuple of (risk_score, injury_list)
        """
        risk = 0.0
        injuries = []

        # Current injury status
        status_risk = {
            "Healthy": 0,
            "Active": 0,
            "Probable": 5,
            "Questionable": 15,
            "Doubtful": 35,
            "Out": 50,
            "IR": 60,
            "PUP": 55,
        }
        risk += status_risk.get(current_status, 10)
        if current_status not in ["Healthy", "Active"]:
            injuries.append(f"Current: {current_status}")

        # Historical injury frequency
        if injury_history:
            # Count significant injuries (caused missed games)
            significant_injuries = [
                inj for inj in injury_history
                if inj.get("games_missed", 0) > 1
            ]
            injury_frequency = len(significant_injuries) / max(len(injury_history), 1)
            risk += injury_frequency * 30

            # Recent injuries more concerning
            recent_injuries = [
                inj for inj in injury_history
                if inj.get("season", 0) >= datetime.now().year - 2
            ]
            for inj in recent_injuries[:3]:  # Top 3 recent
                injuries.append(f"{inj.get('season')}: {inj.get('type', 'Unknown')}")

        # Games missed rate
        miss_rate = 1 - (games_played_recent / max(possible_games, 1))
        risk += miss_rate * 25

        # Specific injury types that increase risk
        high_risk_injuries = ["ACL", "Achilles", "Knee", "Hamstring"]
        for inj in injury_history:
            if any(hi in inj.get("type", "") for hi in high_risk_injuries):
                risk += 5

        return min(100, max(0, risk)), injuries

    def calculate_volatility_risk(
        self,
        weekly_scores: List[float],
    ) -> Tuple[float, float, float, float, float]:
        """
        Calculate volatility/consistency risk.

        Args:
            weekly_scores: List of weekly fantasy scores

        Returns:
            Tuple of (risk_score, cv, boom_rate, bust_rate, floor)
        """
        if not weekly_scores or len(weekly_scores) < 3:
            return 50.0, 0.0, 0.0, 0.0, 0.0

        mean_score = np.mean(weekly_scores)
        std_score = np.std(weekly_scores)

        # Coefficient of variation (lower = more consistent)
        cv = std_score / max(mean_score, 0.1)

        # Boom/bust rates
        boom_threshold = mean_score * 1.5
        bust_threshold = mean_score * 0.5

        boom_rate = sum(1 for s in weekly_scores if s >= boom_threshold) / len(weekly_scores)
        bust_rate = sum(1 for s in weekly_scores if s <= bust_threshold) / len(weekly_scores)

        # Floor (10th percentile)
        floor = np.percentile(weekly_scores, 10)

        # Risk score based on CV
        # CV of 0.3 = low volatility, 0.6 = high volatility
        risk = min(100, cv * 150)

        # Adjust for bust rate
        risk += bust_rate * 30

        return min(100, max(0, risk)), cv, boom_rate, bust_rate, floor

    def calculate_age_risk(
        self,
        age: int,
        position: str,
        years_experience: int,
    ) -> float:
        """
        Calculate age-related decline risk.

        Args:
            age: Player age
            position: Player position
            years_experience: Years in NFL

        Returns:
            Risk score (0-100)
        """
        thresholds = self.AGE_THRESHOLDS.get(
            position,
            {"prime_end": 30, "cliff": 33}
        )

        if age <= thresholds["prime_end"]:
            risk = 0
        elif age <= thresholds["cliff"]:
            # Linear increase from prime end to cliff
            years_past_prime = age - thresholds["prime_end"]
            years_to_cliff = thresholds["cliff"] - thresholds["prime_end"]
            risk = (years_past_prime / years_to_cliff) * 50
        else:
            # Exponential increase after cliff
            years_past_cliff = age - thresholds["cliff"]
            risk = 50 + min(50, years_past_cliff * 15)

        # High-mileage adjustment (lots of experience = more wear)
        if years_experience > 8:
            risk += (years_experience - 8) * 3

        return min(100, max(0, risk))

    def calculate_workload_risk(
        self,
        touches_per_game: float,
        position: str,
        age: int,
    ) -> float:
        """
        Calculate workload sustainability risk.

        Args:
            touches_per_game: Average touches per game
            position: Player position
            age: Player age

        Returns:
            Risk score (0-100)
        """
        # Heavy workload thresholds
        heavy_thresholds = {
            "QB": {"moderate": 35, "heavy": 42},  # Pass attempts
            "RB": {"moderate": 20, "heavy": 25},  # Touches
            "WR": {"moderate": 9, "heavy": 12},   # Targets
            "TE": {"moderate": 7, "heavy": 10},   # Targets
        }

        threshold = heavy_thresholds.get(
            position,
            {"moderate": 15, "heavy": 20}
        )

        if touches_per_game < threshold["moderate"]:
            risk = 0
        elif touches_per_game < threshold["heavy"]:
            risk = 25
        else:
            excess = touches_per_game - threshold["heavy"]
            risk = 50 + min(50, excess * 10)

        # Age multiplier (older players can't handle heavy workloads)
        age_thresholds = self.AGE_THRESHOLDS.get(position, {"prime_end": 30})
        if age > age_thresholds["prime_end"]:
            risk *= 1.3

        return min(100, max(0, risk))

    def calculate_situation_risk(
        self,
        depth_chart_position: int,
        team_changes: List[str],
        qb_situation: str,
        offensive_line_rank: int,
    ) -> float:
        """
        Calculate situational risk factors.

        Args:
            depth_chart_position: Position on depth chart (1 = starter)
            team_changes: List of recent team changes (new coach, etc.)
            qb_situation: QB stability ("stable", "new", "uncertain")
            offensive_line_rank: O-line ranking (1 = best)

        Returns:
            Risk score (0-100)
        """
        risk = 0.0

        # Depth chart security
        if depth_chart_position == 1:
            risk += 0
        elif depth_chart_position == 2:
            risk += 20  # Backup risk
        else:
            risk += 40

        # Team changes create uncertainty
        change_risk = {
            "new_coach": 15,
            "new_oc": 12,
            "new_qb": 10,
            "new_team": 20,
        }
        for change in team_changes:
            risk += change_risk.get(change, 5)

        # QB situation (mainly affects WR/TE)
        qb_risk = {
            "stable": 0,
            "new": 15,
            "uncertain": 25,
            "injured": 30,
        }
        risk += qb_risk.get(qb_situation, 10)

        # Offensive line (mainly affects RB/QB)
        # Rank 1-10 = good, 11-20 = average, 21-32 = bad
        if offensive_line_rank > 20:
            risk += 15
        elif offensive_line_rank > 10:
            risk += 5

        return min(100, max(0, risk))

    def calculate_risk_tier(self, risk_score: float) -> str:
        """Determine risk tier from score."""
        if risk_score < 25:
            return "low"
        elif risk_score < 45:
            return "medium"
        elif risk_score < 65:
            return "high"
        else:
            return "very_high"

    def assess_player(
        self,
        player: Dict,
        weekly_scores: List[float],
        injury_history: List[Dict],
    ) -> RiskAssessment:
        """
        Perform complete risk assessment for a player.

        Args:
            player: Player info dictionary
            weekly_scores: Weekly fantasy scores
            injury_history: Historical injuries

        Returns:
            RiskAssessment object
        """
        position = player.get("position", "RB")
        age = player.get("age", 25)
        experience = player.get("experience", 3)

        # Calculate component risks
        injury_risk, injuries = self.calculate_injury_risk(
            injury_history=injury_history,
            current_status=player.get("injury_status", "Healthy"),
            games_played_recent=player.get("games_played", 15),
        )

        volatility_risk, cv, boom_rate, bust_rate, floor = self.calculate_volatility_risk(
            weekly_scores
        )

        age_risk = self.calculate_age_risk(age, position, experience)

        # Touches per game for workload
        games = max(player.get("games_played", 1), 1)
        touches = player.get("rushing_attempts", 0) + player.get("receptions", 0)
        targets = player.get("targets", 0)
        pass_attempts = player.get("passing_attempts", 0)

        if position == "QB":
            workload_metric = pass_attempts / games
        elif position in ["WR", "TE"]:
            workload_metric = targets / games
        else:
            workload_metric = touches / games

        workload_risk = self.calculate_workload_risk(workload_metric, position, age)

        situation_risk = self.calculate_situation_risk(
            depth_chart_position=player.get("depth_chart_position", 1),
            team_changes=player.get("team_changes", []),
            qb_situation=player.get("qb_situation", "stable"),
            offensive_line_rank=player.get("oline_rank", 16),
        )

        # Weighted overall risk
        weights = self.RISK_WEIGHTS.get(position, self.RISK_WEIGHTS["RB"])
        overall_risk = (
            injury_risk * weights["injury"] +
            volatility_risk * weights["volatility"] +
            age_risk * weights["age"] +
            workload_risk * weights["workload"] +
            situation_risk * weights["situation"]
        )

        # Calculate ceiling
        ceiling = np.percentile(weekly_scores, 90) if weekly_scores else 0

        return RiskAssessment(
            player_id=player.get("player_id", 0),
            name=player.get("name", ""),
            position=position,
            overall_risk_score=round(overall_risk, 1),
            injury_risk=round(injury_risk, 1),
            volatility_risk=round(volatility_risk, 1),
            age_risk=round(age_risk, 1),
            workload_risk=round(workload_risk, 1),
            situation_risk=round(situation_risk, 1),
            injury_history=injuries,
            current_injury_status=player.get("injury_status", "Healthy"),
            games_missed_last_3_years=player.get("games_missed", 0),
            coefficient_of_variation=round(cv, 3),
            age=age,
            years_experience=experience,
            risk_tier=self.calculate_risk_tier(overall_risk),
            boom_rate=round(boom_rate * 100, 1),
            bust_rate=round(bust_rate * 100, 1),
            floor=round(floor, 1),
            ceiling=round(ceiling, 1),
        )

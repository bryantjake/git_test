"""
SQLAlchemy database models for Fantasy Football Ranker.

Stores:
- Player information and stats
- Weekly performance data
- Projections and rankings
- Injury reports
- Game odds/environment data
"""
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    Float,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Index,
    UniqueConstraint,
    Text,
)
from sqlalchemy.orm import (
    declarative_base,
    relationship,
    sessionmaker,
    Session,
)

from config.settings import DB_PATH, DATA_DIR

Base = declarative_base()


class Player(Base):
    """Core player information."""

    __tablename__ = "players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pfr_id = Column(String(50), unique=True, index=True)  # Pro Football Reference ID
    espn_id = Column(String(50), index=True)
    name = Column(String(200), nullable=False, index=True)
    normalized_name = Column(String(200), index=True)  # For matching
    team = Column(String(10))
    position = Column(String(10), index=True)
    age = Column(Integer)
    experience = Column(Integer)  # Years in NFL
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    season_stats = relationship("PlayerStats", back_populates="player", cascade="all, delete-orphan")
    weekly_stats = relationship("WeeklyStats", back_populates="player", cascade="all, delete-orphan")
    projections = relationship("Projection", back_populates="player", cascade="all, delete-orphan")
    injuries = relationship("Injury", back_populates="player", cascade="all, delete-orphan")
    rankings = relationship("Ranking", back_populates="player", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Player(name={self.name}, team={self.team}, position={self.position})>"


class PlayerStats(Base):
    """Season-level player statistics."""

    __tablename__ = "player_stats"
    __table_args__ = (
        UniqueConstraint("player_id", "season", name="uix_player_season"),
        Index("ix_player_stats_season", "season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    season = Column(Integer, nullable=False)

    # Games
    games_played = Column(Integer, default=0)
    games_started = Column(Integer, default=0)

    # Passing
    passing_attempts = Column(Integer, default=0)
    passing_completions = Column(Integer, default=0)
    passing_yards = Column(Integer, default=0)
    passing_tds = Column(Integer, default=0)
    interceptions = Column(Integer, default=0)
    sacks = Column(Integer, default=0)

    # Rushing
    rushing_attempts = Column(Integer, default=0)
    rushing_yards = Column(Integer, default=0)
    rushing_tds = Column(Integer, default=0)

    # Receiving
    targets = Column(Integer, default=0)
    receptions = Column(Integer, default=0)
    receiving_yards = Column(Integer, default=0)
    receiving_tds = Column(Integer, default=0)

    # Fumbles
    fumbles = Column(Integer, default=0)
    fumbles_lost = Column(Integer, default=0)

    # Advanced metrics
    snap_count = Column(Integer, default=0)
    snap_percentage = Column(Float, default=0.0)
    target_share = Column(Float, default=0.0)
    air_yards = Column(Integer, default=0)
    red_zone_targets = Column(Integer, default=0)
    red_zone_touches = Column(Integer, default=0)

    # Calculated fantasy points (stored for different formats)
    fantasy_points_standard = Column(Float, default=0.0)
    fantasy_points_half_ppr = Column(Float, default=0.0)
    fantasy_points_ppr = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    player = relationship("Player", back_populates="season_stats")

    def __repr__(self):
        return f"<PlayerStats(player_id={self.player_id}, season={self.season})>"


class WeeklyStats(Base):
    """Week-level player statistics for game logs."""

    __tablename__ = "weekly_stats"
    __table_args__ = (
        UniqueConstraint("player_id", "season", "week", name="uix_player_week"),
        Index("ix_weekly_stats_season_week", "season", "week"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    season = Column(Integer, nullable=False)
    week = Column(Integer, nullable=False)
    opponent = Column(String(10))
    is_home = Column(Boolean, default=True)
    result = Column(String(20))  # W/L/T with score

    # Passing
    passing_attempts = Column(Integer, default=0)
    passing_completions = Column(Integer, default=0)
    passing_yards = Column(Integer, default=0)
    passing_tds = Column(Integer, default=0)
    interceptions = Column(Integer, default=0)

    # Rushing
    rushing_attempts = Column(Integer, default=0)
    rushing_yards = Column(Integer, default=0)
    rushing_tds = Column(Integer, default=0)

    # Receiving
    targets = Column(Integer, default=0)
    receptions = Column(Integer, default=0)
    receiving_yards = Column(Integer, default=0)
    receiving_tds = Column(Integer, default=0)

    # Misc
    fumbles_lost = Column(Integer, default=0)
    two_pt_conversions = Column(Integer, default=0)

    # Snap data
    snap_count = Column(Integer, default=0)
    snap_percentage = Column(Float, default=0.0)

    # Calculated fantasy points
    fantasy_points_standard = Column(Float, default=0.0)
    fantasy_points_half_ppr = Column(Float, default=0.0)
    fantasy_points_ppr = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    player = relationship("Player", back_populates="weekly_stats")

    def __repr__(self):
        return f"<WeeklyStats(player_id={self.player_id}, season={self.season}, week={self.week})>"


class Projection(Base):
    """Fantasy projections from various sources."""

    __tablename__ = "projections"
    __table_args__ = (
        UniqueConstraint("player_id", "season", "week", "source", name="uix_projection"),
        Index("ix_projections_season_week", "season", "week"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    season = Column(Integer, nullable=False)
    week = Column(Integer, nullable=False)  # 0 = season-long projection
    source = Column(String(50), nullable=False)  # ESPN, Yahoo, etc.

    # Projected stats
    projected_points = Column(Float, default=0.0)
    projected_passing_yards = Column(Float, default=0.0)
    projected_passing_tds = Column(Float, default=0.0)
    projected_interceptions = Column(Float, default=0.0)
    projected_rushing_yards = Column(Float, default=0.0)
    projected_rushing_tds = Column(Float, default=0.0)
    projected_receptions = Column(Float, default=0.0)
    projected_receiving_yards = Column(Float, default=0.0)
    projected_receiving_tds = Column(Float, default=0.0)

    # Ownership data
    roster_percentage = Column(Float, default=0.0)
    start_percentage = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    player = relationship("Player", back_populates="projections")

    def __repr__(self):
        return f"<Projection(player_id={self.player_id}, week={self.week}, source={self.source})>"


class Injury(Base):
    """Injury reports and status."""

    __tablename__ = "injuries"
    __table_args__ = (
        Index("ix_injuries_player_date", "player_id", "report_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    report_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    season = Column(Integer, nullable=False)
    week = Column(Integer)

    injury_status = Column(String(50))  # Out, Questionable, Doubtful, Probable, IR
    injury_type = Column(String(100))  # Body part affected
    injury_details = Column(Text)
    game_status = Column(String(100))  # Expected to play, game-time decision, etc.

    # Practice participation
    wednesday_practice = Column(String(20))  # DNP, Limited, Full
    thursday_practice = Column(String(20))
    friday_practice = Column(String(20))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    player = relationship("Player", back_populates="injuries")

    def __repr__(self):
        return f"<Injury(player_id={self.player_id}, status={self.injury_status})>"


class GameOdds(Base):
    """Vegas odds and game environment data."""

    __tablename__ = "game_odds"
    __table_args__ = (
        UniqueConstraint("season", "week", "home_team", name="uix_game_odds"),
        Index("ix_game_odds_season_week", "season", "week"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String(100))
    season = Column(Integer, nullable=False)
    week = Column(Integer, nullable=False)
    game_date = Column(DateTime)
    home_team = Column(String(10), nullable=False)
    away_team = Column(String(10), nullable=False)

    # Lines
    spread = Column(Float, default=0.0)  # Positive = home underdog
    over_under = Column(Float, default=0.0)
    home_implied_total = Column(Float, default=0.0)
    away_implied_total = Column(Float, default=0.0)

    # Moneylines
    home_moneyline = Column(Integer, default=0)
    away_moneyline = Column(Integer, default=0)
    home_win_probability = Column(Float, default=0.5)
    away_win_probability = Column(Float, default=0.5)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<GameOdds(week={self.week}, {self.away_team}@{self.home_team})>"


class Ranking(Base):
    """Calculated player rankings."""

    __tablename__ = "rankings"
    __table_args__ = (
        UniqueConstraint("player_id", "season", "week", "league_format", name="uix_ranking"),
        Index("ix_rankings_season_week_position", "season", "week", "position"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    season = Column(Integer, nullable=False)
    week = Column(Integer, nullable=False)
    league_format = Column(String(50), default="ppr")  # standard, half_ppr, ppr, superflex
    position = Column(String(10))

    # Rankings
    overall_rank = Column(Integer)
    position_rank = Column(Integer)

    # Component scores (0-100 scale)
    vorp_score = Column(Float, default=0.0)
    opportunity_score = Column(Float, default=0.0)
    efficiency_score = Column(Float, default=0.0)
    schedule_score = Column(Float, default=0.0)
    consistency_score = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)

    # Final composite score
    composite_score = Column(Float, default=0.0)

    # Projected points
    projected_points = Column(Float, default=0.0)

    # Bayesian estimates
    prior_mean = Column(Float, default=0.0)
    posterior_mean = Column(Float, default=0.0)
    uncertainty = Column(Float, default=0.0)  # Standard deviation

    # Tier (for grouping similar players)
    tier = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    player = relationship("Player", back_populates="rankings")

    def __repr__(self):
        return f"<Ranking(player_id={self.player_id}, week={self.week}, rank={self.overall_rank})>"


# Database initialization and session management

_engine = None
_SessionLocal = None


def init_db(db_path: Optional[str] = None) -> None:
    """
    Initialize the database and create all tables.

    Args:
        db_path: Optional custom database path
    """
    global _engine, _SessionLocal

    if db_path is None:
        db_path = str(DB_PATH)

    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    _engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        future=True,
    )

    Base.metadata.create_all(_engine)

    _SessionLocal = sessionmaker(bind=_engine)


def get_session() -> Session:
    """
    Get a database session.

    Returns:
        SQLAlchemy Session object
    """
    global _SessionLocal

    if _SessionLocal is None:
        init_db()

    return _SessionLocal()


@contextmanager
def session_scope():
    """
    Context manager for database sessions.

    Automatically handles commit/rollback and session cleanup.

    Usage:
        with session_scope() as session:
            session.add(player)
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Utility functions for common database operations

def get_or_create_player(
    session: Session,
    name: str,
    team: str,
    position: str,
    pfr_id: Optional[str] = None,
    espn_id: Optional[str] = None,
) -> Player:
    """
    Get existing player or create new one.

    Args:
        session: Database session
        name: Player name
        team: Team abbreviation
        position: Position
        pfr_id: Pro Football Reference ID
        espn_id: ESPN ID

    Returns:
        Player object
    """
    from utils.helpers import normalize_player_name

    normalized = normalize_player_name(name)

    # Try to find by external ID first
    player = None
    if pfr_id:
        player = session.query(Player).filter(Player.pfr_id == pfr_id).first()
    if not player and espn_id:
        player = session.query(Player).filter(Player.espn_id == espn_id).first()

    # Fall back to name matching
    if not player:
        player = session.query(Player).filter(
            Player.normalized_name == normalized,
            Player.position == position,
        ).first()

    if player:
        # Update with any new info
        if pfr_id and not player.pfr_id:
            player.pfr_id = pfr_id
        if espn_id and not player.espn_id:
            player.espn_id = espn_id
        if team:
            player.team = team
        return player

    # Create new player
    player = Player(
        pfr_id=pfr_id,
        espn_id=espn_id,
        name=name,
        normalized_name=normalized,
        team=team,
        position=position,
    )
    session.add(player)
    session.flush()  # Get the ID

    return player

from datetime import datetime
from app import db


class Activity(db.Model):
    """Main activity model storing summary data for each workout."""

    __tablename__ = 'activities'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=True)
    sport = db.Column(db.String(50), nullable=False, default='unknown')
    sub_sport = db.Column(db.String(50), nullable=True)

    # Timing
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    total_elapsed_time = db.Column(db.Float, nullable=True)  # seconds
    total_timer_time = db.Column(db.Float, nullable=True)  # seconds (moving time)

    # Distance and speed
    total_distance = db.Column(db.Float, nullable=True)  # meters
    avg_speed = db.Column(db.Float, nullable=True)  # m/s
    max_speed = db.Column(db.Float, nullable=True)  # m/s

    # Heart rate
    avg_heart_rate = db.Column(db.Integer, nullable=True)  # bpm
    max_heart_rate = db.Column(db.Integer, nullable=True)  # bpm

    # Cadence
    avg_cadence = db.Column(db.Integer, nullable=True)  # rpm or spm
    max_cadence = db.Column(db.Integer, nullable=True)

    # Power (for cycling)
    avg_power = db.Column(db.Integer, nullable=True)  # watts
    max_power = db.Column(db.Integer, nullable=True)
    normalized_power = db.Column(db.Integer, nullable=True)

    # Elevation
    total_ascent = db.Column(db.Float, nullable=True)  # meters
    total_descent = db.Column(db.Float, nullable=True)  # meters
    min_altitude = db.Column(db.Float, nullable=True)  # meters
    max_altitude = db.Column(db.Float, nullable=True)  # meters

    # Calories
    total_calories = db.Column(db.Integer, nullable=True)

    # Training metrics
    training_stress_score = db.Column(db.Float, nullable=True)
    intensity_factor = db.Column(db.Float, nullable=True)

    # GPS bounds
    start_lat = db.Column(db.Float, nullable=True)
    start_lng = db.Column(db.Float, nullable=True)
    end_lat = db.Column(db.Float, nullable=True)
    end_lng = db.Column(db.Float, nullable=True)

    # File info
    original_filename = db.Column(db.String(255), nullable=True)
    file_hash = db.Column(db.String(64), nullable=True, unique=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    laps = db.relationship('ActivityLap', backref='activity', lazy='dynamic', cascade='all, delete-orphan')
    records = db.relationship('ActivityRecord', backref='activity', lazy='dynamic', cascade='all, delete-orphan')
    gps_points = db.relationship('GpsPoint', backref='activity', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self, include_details=False):
        """Convert activity to dictionary."""
        data = {
            'id': self.id,
            'name': self.name or self.default_name,
            'sport': self.sport,
            'sub_sport': self.sub_sport,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_elapsed_time': self.total_elapsed_time,
            'total_timer_time': self.total_timer_time,
            'total_distance': self.total_distance,
            'avg_speed': self.avg_speed,
            'max_speed': self.max_speed,
            'avg_heart_rate': self.avg_heart_rate,
            'max_heart_rate': self.max_heart_rate,
            'avg_cadence': self.avg_cadence,
            'max_cadence': self.max_cadence,
            'avg_power': self.avg_power,
            'max_power': self.max_power,
            'total_ascent': self.total_ascent,
            'total_descent': self.total_descent,
            'min_altitude': self.min_altitude,
            'max_altitude': self.max_altitude,
            'total_calories': self.total_calories,
            'start_lat': self.start_lat,
            'start_lng': self.start_lng,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if include_details:
            data['laps'] = [lap.to_dict() for lap in self.laps]
            data['records'] = [record.to_dict() for record in self.records.limit(5000)]
            data['gps_points'] = [point.to_dict() for point in self.gps_points]

        return data

    @property
    def default_name(self):
        """Generate a default name based on sport and time."""
        if self.start_time:
            time_str = self.start_time.strftime('%B %d, %Y at %I:%M %p')
            return f"{self.sport.title()} - {time_str}"
        return f"{self.sport.title()} Activity"

    @property
    def pace_per_km(self):
        """Calculate pace in min/km."""
        if self.avg_speed and self.avg_speed > 0:
            pace_seconds = 1000 / self.avg_speed
            return pace_seconds / 60
        return None

    @property
    def pace_per_mile(self):
        """Calculate pace in min/mile."""
        if self.avg_speed and self.avg_speed > 0:
            pace_seconds = 1609.34 / self.avg_speed
            return pace_seconds / 60
        return None


class ActivityLap(db.Model):
    """Lap data for activities."""

    __tablename__ = 'activity_laps'

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=False)
    lap_number = db.Column(db.Integer, nullable=False)

    start_time = db.Column(db.DateTime, nullable=True)
    total_elapsed_time = db.Column(db.Float, nullable=True)
    total_timer_time = db.Column(db.Float, nullable=True)
    total_distance = db.Column(db.Float, nullable=True)

    avg_speed = db.Column(db.Float, nullable=True)
    max_speed = db.Column(db.Float, nullable=True)
    avg_heart_rate = db.Column(db.Integer, nullable=True)
    max_heart_rate = db.Column(db.Integer, nullable=True)
    avg_cadence = db.Column(db.Integer, nullable=True)
    max_cadence = db.Column(db.Integer, nullable=True)
    avg_power = db.Column(db.Integer, nullable=True)
    max_power = db.Column(db.Integer, nullable=True)

    total_ascent = db.Column(db.Float, nullable=True)
    total_descent = db.Column(db.Float, nullable=True)
    total_calories = db.Column(db.Integer, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'lap_number': self.lap_number,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'total_elapsed_time': self.total_elapsed_time,
            'total_timer_time': self.total_timer_time,
            'total_distance': self.total_distance,
            'avg_speed': self.avg_speed,
            'max_speed': self.max_speed,
            'avg_heart_rate': self.avg_heart_rate,
            'max_heart_rate': self.max_heart_rate,
            'avg_cadence': self.avg_cadence,
            'avg_power': self.avg_power,
            'total_ascent': self.total_ascent,
            'total_descent': self.total_descent,
            'total_calories': self.total_calories,
        }


class ActivityRecord(db.Model):
    """Time-series data points for activities (heart rate, speed, etc.)."""

    __tablename__ = 'activity_records'

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=False)

    timestamp = db.Column(db.DateTime, nullable=False)
    elapsed_time = db.Column(db.Float, nullable=True)  # seconds from start
    distance = db.Column(db.Float, nullable=True)  # cumulative meters

    heart_rate = db.Column(db.Integer, nullable=True)
    speed = db.Column(db.Float, nullable=True)
    cadence = db.Column(db.Integer, nullable=True)
    power = db.Column(db.Integer, nullable=True)
    altitude = db.Column(db.Float, nullable=True)
    temperature = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'elapsed_time': self.elapsed_time,
            'distance': self.distance,
            'heart_rate': self.heart_rate,
            'speed': self.speed,
            'cadence': self.cadence,
            'power': self.power,
            'altitude': self.altitude,
            'temperature': self.temperature,
        }


class GpsPoint(db.Model):
    """GPS coordinates for mapping activities."""

    __tablename__ = 'gps_points'

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=False)

    timestamp = db.Column(db.DateTime, nullable=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    altitude = db.Column(db.Float, nullable=True)
    elapsed_time = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            'lat': self.latitude,
            'lng': self.longitude,
            'altitude': self.altitude,
            'elapsed_time': self.elapsed_time,
        }

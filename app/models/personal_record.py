from datetime import datetime
from app import db


class PersonalRecord(db.Model):
    """Personal records for various distances and metrics."""

    __tablename__ = 'personal_records'

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=False)

    sport = db.Column(db.String(50), nullable=False)
    record_type = db.Column(db.String(50), nullable=False)  # 'distance', 'time', 'speed', 'power'
    record_name = db.Column(db.String(100), nullable=False)  # '5K', '10K', 'Marathon', 'Max HR', etc.

    value = db.Column(db.Float, nullable=False)  # The record value
    unit = db.Column(db.String(20), nullable=False)  # 'seconds', 'meters', 'm/s', 'watts', 'bpm'

    achieved_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    activity = db.relationship('Activity', backref=db.backref('personal_records', lazy='dynamic'))

    # Ensure unique records per type/name/sport combination
    __table_args__ = (
        db.UniqueConstraint('sport', 'record_type', 'record_name', name='unique_record'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'activity_id': self.activity_id,
            'sport': self.sport,
            'record_type': self.record_type,
            'record_name': self.record_name,
            'value': self.value,
            'unit': self.unit,
            'achieved_at': self.achieved_at.isoformat() if self.achieved_at else None,
            'formatted_value': self.formatted_value,
        }

    @property
    def formatted_value(self):
        """Return human-readable formatted value."""
        if self.unit == 'seconds':
            # Format as HH:MM:SS or MM:SS
            total_seconds = int(self.value)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            if hours > 0:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            return f"{minutes}:{seconds:02d}"
        elif self.unit == 'meters':
            if self.value >= 1000:
                return f"{self.value / 1000:.2f} km"
            return f"{self.value:.0f} m"
        elif self.unit == 'm/s':
            # Convert to km/h
            kmh = self.value * 3.6
            return f"{kmh:.1f} km/h"
        elif self.unit == 'watts':
            return f"{int(self.value)} W"
        elif self.unit == 'bpm':
            return f"{int(self.value)} bpm"
        return str(self.value)


# Standard distance records to track
STANDARD_DISTANCES = {
    'running': [
        ('1K', 1000),
        ('1 Mile', 1609.34),
        ('5K', 5000),
        ('10K', 10000),
        ('Half Marathon', 21097.5),
        ('Marathon', 42195),
    ],
    'cycling': [
        ('10K', 10000),
        ('20K', 20000),
        ('40K', 40000),
        ('100K', 100000),
    ],
}

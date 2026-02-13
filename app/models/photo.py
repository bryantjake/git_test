from app import db
from datetime import datetime


class Photo(db.Model):
    __tablename__ = 'photos'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    location_name = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self, include_answers=False):
        data = {
            'id': self.id,
            'filename': self.filename,
            'description': self.description,
        }
        if include_answers:
            data['year'] = self.year
            data['latitude'] = self.latitude
            data['longitude'] = self.longitude
            data['location_name'] = self.location_name
        return data

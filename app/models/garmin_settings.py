"""
Garmin Connect settings and sync status model.
"""

import os
import json
from datetime import datetime
from cryptography.fernet import Fernet
from app import db


def get_encryption_key():
    """Get or generate encryption key for storing tokens."""
    key = os.environ.get('GARMIN_ENCRYPTION_KEY')
    if not key:
        # In production, this should be set as an environment variable
        # For development, we generate a key (but it won't persist across restarts)
        key = Fernet.generate_key().decode()
        os.environ['GARMIN_ENCRYPTION_KEY'] = key
    return key.encode() if isinstance(key, str) else key


class GarminSettings(db.Model):
    """Store Garmin Connect settings and session tokens."""

    __tablename__ = 'garmin_settings'

    id = db.Column(db.Integer, primary_key=True)

    # User info from Garmin
    garmin_display_name = db.Column(db.String(255), nullable=True)
    garmin_email = db.Column(db.String(255), nullable=True)

    # Encrypted session tokens (not password - we store OAuth tokens)
    _session_tokens = db.Column('session_tokens', db.Text, nullable=True)

    # Sync settings
    auto_sync_enabled = db.Column(db.Boolean, default=False)
    sync_interval_minutes = db.Column(db.Integer, default=60)  # Default: every hour
    sync_days_back = db.Column(db.Integer, default=7)  # How many days to look back

    # Status
    is_connected = db.Column(db.Boolean, default=False)
    last_sync_at = db.Column(db.DateTime, nullable=True)
    last_sync_status = db.Column(db.String(50), nullable=True)  # 'success', 'failed', 'in_progress'
    last_sync_message = db.Column(db.Text, nullable=True)
    last_sync_count = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def session_tokens(self):
        """Decrypt and return session tokens."""
        if not self._session_tokens:
            return None
        try:
            fernet = Fernet(get_encryption_key())
            decrypted = fernet.decrypt(self._session_tokens.encode())
            return json.loads(decrypted.decode())
        except Exception:
            return None

    @session_tokens.setter
    def session_tokens(self, value):
        """Encrypt and store session tokens."""
        if value is None:
            self._session_tokens = None
        else:
            try:
                fernet = Fernet(get_encryption_key())
                encrypted = fernet.encrypt(json.dumps(value).encode())
                self._session_tokens = encrypted.decode()
            except Exception:
                self._session_tokens = None

    def to_dict(self):
        """Convert to dictionary (without sensitive data)."""
        return {
            'id': self.id,
            'garmin_display_name': self.garmin_display_name,
            'garmin_email': self.garmin_email,
            'auto_sync_enabled': self.auto_sync_enabled,
            'sync_interval_minutes': self.sync_interval_minutes,
            'sync_days_back': self.sync_days_back,
            'is_connected': self.is_connected,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'last_sync_status': self.last_sync_status,
            'last_sync_message': self.last_sync_message,
            'last_sync_count': self.last_sync_count,
        }

    @staticmethod
    def get_settings():
        """Get or create the singleton settings record."""
        settings = GarminSettings.query.first()
        if not settings:
            settings = GarminSettings()
            db.session.add(settings)
            db.session.commit()
        return settings


class SyncLog(db.Model):
    """Log of sync operations for history and debugging."""

    __tablename__ = 'sync_logs'

    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='in_progress')  # 'success', 'failed', 'in_progress'

    activities_synced = db.Column(db.Integer, default=0)
    activities_skipped = db.Column(db.Integer, default=0)
    activities_failed = db.Column(db.Integer, default=0)

    error_message = db.Column(db.Text, nullable=True)
    details = db.Column(db.Text, nullable=True)  # JSON string with detailed results

    def to_dict(self):
        return {
            'id': self.id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status,
            'activities_synced': self.activities_synced,
            'activities_skipped': self.activities_skipped,
            'activities_failed': self.activities_failed,
            'error_message': self.error_message,
        }

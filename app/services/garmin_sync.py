"""
Garmin Connect sync service for automatic activity downloads.
"""

import os
import tempfile
from datetime import datetime, timedelta
from garminconnect import Garmin, GarminConnectAuthenticationError
from app import db
from app.models import Activity
from app.services.fit_parser import FitParser
from app.services.records_service import RecordsService


class GarminSyncService:
    """Service for syncing activities from Garmin Connect."""

    def __init__(self):
        self.client = None
        self._logged_in = False

    def login(self, email, password):
        """
        Login to Garmin Connect.

        Args:
            email: Garmin Connect email
            password: Garmin Connect password

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            self.client = Garmin(email, password)
            self.client.login()
            self._logged_in = True
            return True, "Successfully logged in to Garmin Connect"
        except GarminConnectAuthenticationError as e:
            self._logged_in = False
            return False, f"Authentication failed: {str(e)}"
        except Exception as e:
            self._logged_in = False
            return False, f"Login failed: {str(e)}"

    def login_with_token(self, token_data):
        """
        Login using stored session tokens (avoids re-authentication).

        Args:
            token_data: Dictionary containing oauth tokens

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            self.client = Garmin()
            self.client.login(token_data)
            self._logged_in = True
            return True, "Session restored successfully"
        except Exception as e:
            self._logged_in = False
            return False, f"Session restore failed: {str(e)}"

    def get_session_tokens(self):
        """Get current session tokens for storage."""
        if self.client and self._logged_in:
            return self.client.garth.dumps()
        return None

    @property
    def is_logged_in(self):
        return self._logged_in and self.client is not None

    def get_activities_list(self, limit=20, start=0):
        """
        Get list of recent activities from Garmin Connect.

        Args:
            limit: Number of activities to fetch
            start: Starting offset

        Returns:
            list: List of activity summaries
        """
        if not self.is_logged_in:
            raise Exception("Not logged in to Garmin Connect")

        try:
            activities = self.client.get_activities(start, limit)
            return activities
        except Exception as e:
            raise Exception(f"Failed to fetch activities: {str(e)}")

    def download_activity(self, activity_id):
        """
        Download a single activity FIT file.

        Args:
            activity_id: Garmin activity ID

        Returns:
            bytes: FIT file data
        """
        if not self.is_logged_in:
            raise Exception("Not logged in to Garmin Connect")

        try:
            fit_data = self.client.download_activity(
                activity_id,
                dl_fmt=self.client.ActivityDownloadFormat.ORIGINAL
            )
            return fit_data
        except Exception as e:
            raise Exception(f"Failed to download activity {activity_id}: {str(e)}")

    def sync_recent_activities(self, days=7, limit=50):
        """
        Sync recent activities from Garmin Connect.

        Args:
            days: Number of days to look back
            limit: Maximum number of activities to sync

        Returns:
            dict: Sync results with counts and details
        """
        if not self.is_logged_in:
            raise Exception("Not logged in to Garmin Connect")

        results = {
            'synced': 0,
            'skipped': 0,
            'failed': 0,
            'new_records': [],
            'activities': [],
            'errors': []
        }

        try:
            # Get recent activities from Garmin
            activities = self.get_activities_list(limit=limit)

            # Filter to recent days
            cutoff_date = datetime.now() - timedelta(days=days)

            for garmin_activity in activities:
                try:
                    # Parse activity date
                    activity_date = datetime.fromisoformat(
                        garmin_activity['startTimeLocal'].replace('Z', '+00:00')
                    )

                    # Skip if older than cutoff
                    if activity_date.replace(tzinfo=None) < cutoff_date:
                        continue

                    activity_id = garmin_activity['activityId']
                    activity_name = garmin_activity.get('activityName', 'Untitled')

                    # Check if we already have this activity (by Garmin ID)
                    # We store Garmin ID in original_filename field as "garmin_<id>"
                    existing = Activity.query.filter(
                        Activity.original_filename == f"garmin_{activity_id}"
                    ).first()

                    if existing:
                        results['skipped'] += 1
                        continue

                    # Download the FIT file
                    fit_data = self.download_activity(activity_id)

                    # Save to temp file and parse
                    with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
                        f.write(fit_data)
                        temp_path = f.name

                    try:
                        # Parse the FIT file
                        parser = FitParser(temp_path, f"garmin_{activity_id}")
                        activity, is_new = parser.parse()

                        if is_new:
                            # Update with Garmin activity name if not set
                            if not activity.name:
                                activity.name = activity_name
                            db.session.commit()

                            # Check for personal records
                            new_records = RecordsService.check_and_update_records(activity)

                            results['synced'] += 1
                            results['activities'].append({
                                'id': activity.id,
                                'name': activity.name,
                                'sport': activity.sport,
                                'garmin_id': activity_id
                            })

                            if new_records:
                                results['new_records'].extend([r.to_dict() for r in new_records])
                        else:
                            results['skipped'] += 1

                    finally:
                        # Clean up temp file
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'activity_id': garmin_activity.get('activityId'),
                        'error': str(e)
                    })

        except Exception as e:
            raise Exception(f"Sync failed: {str(e)}")

        return results

    def get_user_profile(self):
        """Get the logged-in user's profile info."""
        if not self.is_logged_in:
            raise Exception("Not logged in to Garmin Connect")

        try:
            return self.client.get_full_name()
        except Exception:
            return None


# Global instance for the sync service
_sync_service = None


def get_sync_service():
    """Get or create the global sync service instance."""
    global _sync_service
    if _sync_service is None:
        _sync_service = GarminSyncService()
    return _sync_service

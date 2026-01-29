"""
Background scheduler for automatic Garmin sync.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None
app_context = None


def init_scheduler(app):
    """Initialize the background scheduler."""
    global scheduler, app_context

    if scheduler is not None:
        return

    app_context = app.app_context

    scheduler = BackgroundScheduler()
    scheduler.start()

    # Schedule initial sync check
    with app.app_context():
        update_sync_schedule()

    logger.info("Background scheduler initialized")


def update_sync_schedule():
    """Update the sync schedule based on current settings."""
    global scheduler

    if scheduler is None:
        return

    # Remove existing sync job if any
    try:
        scheduler.remove_job('garmin_sync')
    except Exception:
        pass

    # Get current settings
    from app.models import GarminSettings
    settings = GarminSettings.get_settings()

    if settings.auto_sync_enabled and settings.is_connected:
        # Add new sync job
        scheduler.add_job(
            run_sync_job,
            trigger=IntervalTrigger(minutes=settings.sync_interval_minutes),
            id='garmin_sync',
            name='Garmin Auto Sync',
            replace_existing=True
        )
        logger.info(f"Auto-sync scheduled every {settings.sync_interval_minutes} minutes")
    else:
        logger.info("Auto-sync disabled")


def run_sync_job():
    """Execute the sync job."""
    global app_context

    if app_context is None:
        logger.error("No app context available for sync job")
        return

    with app_context():
        try:
            from app import db
            from app.models import GarminSettings, SyncLog
            from app.services import get_sync_service
            import json

            settings = GarminSettings.get_settings()

            if not settings.auto_sync_enabled or not settings.is_connected:
                logger.info("Auto-sync is disabled or not connected")
                return

            sync_service = get_sync_service()

            # Try to restore session
            if not sync_service.is_logged_in:
                if settings.session_tokens:
                    success, message = sync_service.login_with_token(settings.session_tokens)
                    if not success:
                        logger.error(f"Failed to restore session: {message}")
                        settings.last_sync_status = 'failed'
                        settings.last_sync_message = f"Session restore failed: {message}"
                        settings.last_sync_at = datetime.utcnow()
                        db.session.commit()
                        return
                else:
                    logger.error("No session tokens available")
                    return

            # Create sync log
            sync_log = SyncLog(status='in_progress')
            db.session.add(sync_log)
            db.session.commit()

            # Perform sync
            results = sync_service.sync_recent_activities(
                days=settings.sync_days_back,
                limit=50
            )

            # Update sync log
            sync_log.status = 'success'
            sync_log.completed_at = datetime.utcnow()
            sync_log.activities_synced = results['synced']
            sync_log.activities_skipped = results['skipped']
            sync_log.activities_failed = results['failed']
            sync_log.details = json.dumps(results)

            # Update settings
            settings.last_sync_at = datetime.utcnow()
            settings.last_sync_status = 'success'
            settings.last_sync_message = f"Auto-synced {results['synced']} activities"
            settings.last_sync_count = results['synced']

            # Update session tokens
            new_tokens = sync_service.get_session_tokens()
            if new_tokens:
                settings.session_tokens = new_tokens

            db.session.commit()

            logger.info(f"Auto-sync completed: {results['synced']} synced, {results['skipped']} skipped")

        except Exception as e:
            logger.error(f"Auto-sync failed: {str(e)}")

            try:
                from app import db
                from app.models import GarminSettings

                settings = GarminSettings.get_settings()
                settings.last_sync_at = datetime.utcnow()
                settings.last_sync_status = 'failed'
                settings.last_sync_message = str(e)
                db.session.commit()
            except Exception:
                pass


def get_scheduler_status():
    """Get current scheduler status."""
    global scheduler

    if scheduler is None:
        return {'running': False, 'jobs': []}

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None
        })

    return {
        'running': scheduler.running,
        'jobs': jobs
    }

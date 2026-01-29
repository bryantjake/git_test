"""
Garmin Connect API routes for syncing activities.
"""

import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from app import db
from app.models import GarminSettings, SyncLog
from app.services import get_sync_service

garmin_bp = Blueprint('garmin', __name__)


@garmin_bp.route('/status', methods=['GET'])
def get_status():
    """Get current Garmin connection status."""
    settings = GarminSettings.get_settings()
    sync_service = get_sync_service()

    return jsonify({
        'settings': settings.to_dict(),
        'is_session_active': sync_service.is_logged_in
    })


@garmin_bp.route('/connect', methods=['POST'])
def connect():
    """
    Connect to Garmin Connect with email/password.
    Stores session tokens for future use.
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    sync_service = get_sync_service()
    success, message = sync_service.login(email, password)

    if success:
        # Get and store session tokens
        settings = GarminSettings.get_settings()
        settings.session_tokens = sync_service.get_session_tokens()
        settings.garmin_email = email
        settings.is_connected = True

        # Try to get display name
        try:
            display_name = sync_service.get_user_profile()
            settings.garmin_display_name = display_name
        except Exception:
            pass

        db.session.commit()

        return jsonify({
            'success': True,
            'message': message,
            'settings': settings.to_dict()
        })
    else:
        return jsonify({
            'success': False,
            'error': message
        }), 401


@garmin_bp.route('/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from Garmin Connect and clear stored tokens."""
    settings = GarminSettings.get_settings()

    settings.session_tokens = None
    settings.is_connected = False
    settings.garmin_display_name = None
    settings.auto_sync_enabled = False

    db.session.commit()

    # Reset the sync service
    global _sync_service
    from app.services.garmin_sync import _sync_service
    _sync_service = None

    return jsonify({
        'success': True,
        'message': 'Disconnected from Garmin Connect'
    })


@garmin_bp.route('/restore-session', methods=['POST'])
def restore_session():
    """Restore session from stored tokens."""
    settings = GarminSettings.get_settings()

    if not settings.session_tokens:
        return jsonify({
            'success': False,
            'error': 'No stored session tokens'
        }), 400

    sync_service = get_sync_service()
    success, message = sync_service.login_with_token(settings.session_tokens)

    if success:
        # Update tokens in case they were refreshed
        new_tokens = sync_service.get_session_tokens()
        if new_tokens:
            settings.session_tokens = new_tokens
            db.session.commit()

        return jsonify({
            'success': True,
            'message': message
        })
    else:
        # Clear invalid tokens
        settings.session_tokens = None
        settings.is_connected = False
        db.session.commit()

        return jsonify({
            'success': False,
            'error': message
        }), 401


@garmin_bp.route('/sync', methods=['POST'])
def sync_activities():
    """
    Sync recent activities from Garmin Connect.
    """
    settings = GarminSettings.get_settings()
    sync_service = get_sync_service()

    # Try to restore session if not logged in
    if not sync_service.is_logged_in:
        if settings.session_tokens:
            success, _ = sync_service.login_with_token(settings.session_tokens)
            if not success:
                return jsonify({
                    'success': False,
                    'error': 'Session expired. Please reconnect to Garmin.'
                }), 401
        else:
            return jsonify({
                'success': False,
                'error': 'Not connected to Garmin Connect'
            }), 401

    # Get sync parameters
    data = request.get_json() or {}
    days = data.get('days', settings.sync_days_back)
    limit = data.get('limit', 50)

    # Create sync log entry
    sync_log = SyncLog(status='in_progress')
    db.session.add(sync_log)
    db.session.commit()

    try:
        # Perform sync
        results = sync_service.sync_recent_activities(days=days, limit=limit)

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
        settings.last_sync_message = f"Synced {results['synced']} activities"
        settings.last_sync_count = results['synced']

        # Update session tokens
        new_tokens = sync_service.get_session_tokens()
        if new_tokens:
            settings.session_tokens = new_tokens

        db.session.commit()

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        # Update sync log with error
        sync_log.status = 'failed'
        sync_log.completed_at = datetime.utcnow()
        sync_log.error_message = str(e)

        # Update settings
        settings.last_sync_at = datetime.utcnow()
        settings.last_sync_status = 'failed'
        settings.last_sync_message = str(e)

        db.session.commit()

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@garmin_bp.route('/settings', methods=['GET'])
def get_settings():
    """Get Garmin sync settings."""
    settings = GarminSettings.get_settings()
    return jsonify(settings.to_dict())


@garmin_bp.route('/settings', methods=['PATCH'])
def update_settings():
    """Update Garmin sync settings."""
    settings = GarminSettings.get_settings()
    data = request.get_json()

    if 'auto_sync_enabled' in data:
        settings.auto_sync_enabled = data['auto_sync_enabled']

    if 'sync_interval_minutes' in data:
        # Minimum 15 minutes, maximum 24 hours
        interval = max(15, min(1440, data['sync_interval_minutes']))
        settings.sync_interval_minutes = interval

    if 'sync_days_back' in data:
        # Minimum 1 day, maximum 30 days
        days = max(1, min(30, data['sync_days_back']))
        settings.sync_days_back = days

    db.session.commit()

    # If auto-sync setting changed, update scheduler
    if 'auto_sync_enabled' in data:
        from app.scheduler import update_sync_schedule
        update_sync_schedule()

    return jsonify(settings.to_dict())


@garmin_bp.route('/sync-logs', methods=['GET'])
def get_sync_logs():
    """Get recent sync logs."""
    limit = request.args.get('limit', 10, type=int)

    logs = SyncLog.query.order_by(SyncLog.started_at.desc()).limit(limit).all()

    return jsonify([log.to_dict() for log in logs])


@garmin_bp.route('/activities', methods=['GET'])
def get_garmin_activities():
    """
    Get list of activities from Garmin Connect (without downloading).
    Useful for previewing what's available.
    """
    sync_service = get_sync_service()
    settings = GarminSettings.get_settings()

    # Try to restore session if not logged in
    if not sync_service.is_logged_in:
        if settings.session_tokens:
            success, _ = sync_service.login_with_token(settings.session_tokens)
            if not success:
                return jsonify({
                    'error': 'Session expired. Please reconnect to Garmin.'
                }), 401
        else:
            return jsonify({
                'error': 'Not connected to Garmin Connect'
            }), 401

    limit = request.args.get('limit', 20, type=int)

    try:
        activities = sync_service.get_activities_list(limit=limit)

        # Format activities for response
        formatted = []
        for a in activities:
            formatted.append({
                'garmin_id': a.get('activityId'),
                'name': a.get('activityName'),
                'sport': a.get('activityType', {}).get('typeKey', 'unknown'),
                'start_time': a.get('startTimeLocal'),
                'distance': a.get('distance'),
                'duration': a.get('duration'),
                'calories': a.get('calories'),
            })

        return jsonify(formatted)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

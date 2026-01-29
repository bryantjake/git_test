import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app import db
from app.models import Activity, PersonalRecord
from app.services import FitParser, StatsService, RecordsService

api_bp = Blueprint('api', __name__)


def allowed_file(filename):
    """Check if file has allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'fit'


# ============ Activity Endpoints ============

@api_bp.route('/activities', methods=['GET'])
def get_activities():
    """Get all activities with optional filters."""
    sport = request.args.get('sport')
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = Activity.query

    if sport:
        query = query.filter_by(sport=sport)

    if year:
        from sqlalchemy import extract
        query = query.filter(extract('year', Activity.start_time) == year)

    if month:
        from sqlalchemy import extract
        query = query.filter(extract('month', Activity.start_time) == month)

    # Order by most recent first
    query = query.order_by(Activity.start_time.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'activities': [a.to_dict() for a in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    })


@api_bp.route('/activities/<int:activity_id>', methods=['GET'])
def get_activity(activity_id):
    """Get a single activity with full details."""
    activity = Activity.query.get_or_404(activity_id)
    include_details = request.args.get('details', 'true').lower() == 'true'
    return jsonify(activity.to_dict(include_details=include_details))


@api_bp.route('/activities/<int:activity_id>', methods=['DELETE'])
def delete_activity(activity_id):
    """Delete an activity."""
    activity = Activity.query.get_or_404(activity_id)
    db.session.delete(activity)
    db.session.commit()
    return jsonify({'message': 'Activity deleted successfully'})


@api_bp.route('/activities/<int:activity_id>', methods=['PATCH'])
def update_activity(activity_id):
    """Update activity name."""
    activity = Activity.query.get_or_404(activity_id)
    data = request.get_json()

    if 'name' in data:
        activity.name = data['name']

    db.session.commit()
    return jsonify(activity.to_dict())


# ============ Upload Endpoint ============

@api_bp.route('/upload', methods=['POST'])
def upload_file():
    """Upload and process a FIT file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only .fit files are allowed'}), 400

    # Save file temporarily
    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        # Parse the FIT file
        parser = FitParser(filepath, filename)
        activity, is_new = parser.parse()

        if not is_new:
            return jsonify({
                'message': 'Activity already exists',
                'activity': activity.to_dict(),
                'is_duplicate': True
            })

        # Check for personal records
        new_records = RecordsService.check_and_update_records(activity)

        return jsonify({
            'message': 'Activity uploaded successfully',
            'activity': activity.to_dict(),
            'new_records': [r.to_dict() for r in new_records],
            'is_duplicate': False
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        # Clean up uploaded file
        if os.path.exists(filepath):
            os.remove(filepath)


@api_bp.route('/upload/batch', methods=['POST'])
def upload_batch():
    """Upload multiple FIT files."""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    results = []

    for file in files:
        if file.filename == '' or not allowed_file(file.filename):
            results.append({
                'filename': file.filename,
                'success': False,
                'error': 'Invalid file'
            })
            continue

        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            parser = FitParser(filepath, filename)
            activity, is_new = parser.parse()

            if is_new:
                RecordsService.check_and_update_records(activity)

            results.append({
                'filename': filename,
                'success': True,
                'activity_id': activity.id,
                'is_duplicate': not is_new
            })

        except Exception as e:
            results.append({
                'filename': filename,
                'success': False,
                'error': str(e)
            })

        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    return jsonify({
        'results': results,
        'total': len(files),
        'successful': sum(1 for r in results if r['success']),
        'failed': sum(1 for r in results if not r['success'])
    })


# ============ Statistics Endpoints ============

@api_bp.route('/stats/summary', methods=['GET'])
def get_summary():
    """Get overall statistics summary."""
    return jsonify(StatsService.get_all_time_stats())


@api_bp.route('/stats/weekly', methods=['GET'])
def get_weekly_stats():
    """Get weekly statistics."""
    year = request.args.get('year', type=int)
    week = request.args.get('week', type=int)
    return jsonify(StatsService.get_weekly_summary(year, week))


@api_bp.route('/stats/monthly', methods=['GET'])
def get_monthly_stats():
    """Get monthly statistics."""
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    return jsonify(StatsService.get_monthly_summary(year, month))


@api_bp.route('/stats/annual', methods=['GET'])
def get_annual_stats():
    """Get annual statistics."""
    year = request.args.get('year', type=int)
    return jsonify(StatsService.get_annual_summary(year))


@api_bp.route('/stats/yearly-comparison', methods=['GET'])
def get_yearly_comparison():
    """Get comparison across multiple years."""
    years_param = request.args.get('years')
    years = None
    if years_param:
        years = [int(y) for y in years_param.split(',')]
    return jsonify(StatsService.get_yearly_comparison(years))


@api_bp.route('/stats/monthly-trend', methods=['GET'])
def get_monthly_trend():
    """Get monthly trend for a year."""
    year = request.args.get('year', type=int)
    return jsonify(StatsService.get_monthly_trend(year))


@api_bp.route('/stats/heatmap', methods=['GET'])
def get_heatmap():
    """Get activity heatmap data."""
    year = request.args.get('year', type=int)
    return jsonify(StatsService.get_activity_heatmap_data(year))


# ============ Personal Records Endpoints ============

@api_bp.route('/records', methods=['GET'])
def get_records():
    """Get all personal records."""
    sport = request.args.get('sport')
    return jsonify(RecordsService.get_all_records(sport))


@api_bp.route('/records/activity/<int:activity_id>', methods=['GET'])
def get_activity_records(activity_id):
    """Get records achieved in a specific activity."""
    return jsonify(RecordsService.get_records_for_activity(activity_id))


# ============ Comparison Endpoints ============

@api_bp.route('/compare', methods=['GET'])
def compare_activities():
    """Compare multiple activities."""
    activity_ids = request.args.get('ids', '')
    if not activity_ids:
        return jsonify({'error': 'No activity IDs provided'}), 400

    try:
        ids = [int(id) for id in activity_ids.split(',')]
    except ValueError:
        return jsonify({'error': 'Invalid activity IDs'}), 400

    activities = Activity.query.filter(Activity.id.in_(ids)).all()

    if not activities:
        return jsonify({'error': 'No activities found'}), 404

    # Build comparison data
    comparison = {
        'activities': [a.to_dict(include_details=True) for a in activities],
        'metrics': {
            'distance': [a.total_distance for a in activities],
            'duration': [a.total_timer_time for a in activities],
            'avg_speed': [a.avg_speed for a in activities],
            'avg_heart_rate': [a.avg_heart_rate for a in activities],
            'total_ascent': [a.total_ascent for a in activities],
            'calories': [a.total_calories for a in activities],
        }
    }

    return jsonify(comparison)


# ============ Sports Endpoints ============

@api_bp.route('/sports', methods=['GET'])
def get_sports():
    """Get list of all sports with activity counts."""
    from sqlalchemy import func

    sports = db.session.query(
        Activity.sport,
        func.count(Activity.id).label('count')
    ).group_by(Activity.sport).all()

    return jsonify([{
        'sport': sport,
        'count': count
    } for sport, count in sports])

from flask import Blueprint, render_template, request
from app.models import Activity, PersonalRecord
from app.services import StatsService

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Dashboard homepage."""
    return render_template('index.html')


@main_bp.route('/activities')
def activities():
    """Activity list page."""
    return render_template('activities.html')


@main_bp.route('/activity/<int:activity_id>')
def activity_detail(activity_id):
    """Activity detail page."""
    activity = Activity.query.get_or_404(activity_id)
    return render_template('activity_detail.html', activity=activity)


@main_bp.route('/compare')
def compare():
    """Activity comparison page."""
    return render_template('compare.html')


@main_bp.route('/records')
def records():
    """Personal records page."""
    return render_template('records.html')


@main_bp.route('/stats')
def stats():
    """Statistics and summaries page."""
    return render_template('stats.html')


@main_bp.route('/upload')
def upload():
    """Upload page."""
    return render_template('upload.html')


@main_bp.route('/settings')
def settings():
    """Settings page for Garmin sync."""
    return render_template('settings.html')

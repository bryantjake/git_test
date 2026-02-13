from flask import Blueprint, render_template, jsonify

main_bp = Blueprint('main', __name__)


@main_bp.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/play')
def play():
    return render_template('play.html')


@main_bp.route('/upload')
def upload():
    return render_template('upload.html')

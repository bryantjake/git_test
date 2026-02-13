import uuid
import math
from flask import Blueprint, request, jsonify, Response
from app import db
from app.models import Photo

api_bp = Blueprint('api', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

CONTENT_TYPES = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'gif': 'image/gif',
    'webp': 'image/webp',
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@api_bp.route('/photos/file/<filename>')
def serve_photo(filename):
    photo = Photo.query.filter_by(filename=filename).first_or_404()
    return Response(photo.image_data, mimetype=photo.content_type)


@api_bp.route('/photos', methods=['GET'])
def get_photos():
    photos = Photo.query.order_by(Photo.created_at.desc()).all()
    return jsonify([p.to_dict(include_answers=True) for p in photos])


@api_bp.route('/photos', methods=['POST'])
def upload_photo():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, webp'}), 400

    year = request.form.get('year', type=int)
    latitude = request.form.get('latitude', type=float)
    longitude = request.form.get('longitude', type=float)
    location_name = request.form.get('location_name', '').strip()
    description = request.form.get('description', '').strip()

    if not year or latitude is None or longitude is None:
        return jsonify({'error': 'Year, latitude, and longitude are required'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    image_bytes = file.read()

    photo = Photo(
        filename=filename,
        content_type=CONTENT_TYPES.get(ext, 'image/jpeg'),
        image_data=image_bytes,
        year=year,
        latitude=latitude,
        longitude=longitude,
        location_name=location_name or None,
        description=description or None,
    )
    db.session.add(photo)
    db.session.commit()

    return jsonify(photo.to_dict(include_answers=True)), 201


@api_bp.route('/photos/<int:photo_id>', methods=['DELETE'])
def delete_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    db.session.delete(photo)
    db.session.commit()
    return jsonify({'message': 'Photo deleted'})


@api_bp.route('/game/new', methods=['GET'])
def new_game():
    count = Photo.query.count()
    if count < 1:
        return jsonify({'error': 'Not enough photos. Upload at least 1 photo to play.'}), 400

    rounds = min(5, count)
    photos = Photo.query.order_by(db.func.random()).limit(rounds).all()

    return jsonify({
        'rounds': rounds,
        'photos': [p.to_dict(include_answers=False) for p in photos],
    })


@api_bp.route('/game/score', methods=['POST'])
def score_guess():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    photo_id = data.get('photo_id')
    guessed_year = data.get('year')
    guessed_lat = data.get('latitude')
    guessed_lng = data.get('longitude')

    if photo_id is None or guessed_year is None or guessed_lat is None or guessed_lng is None:
        return jsonify({'error': 'photo_id, year, latitude, and longitude are required'}), 400

    photo = Photo.query.get_or_404(photo_id)

    # Year scoring: exponential decay, 5000 max
    year_diff = abs(guessed_year - photo.year)
    if year_diff == 0:
        year_score = 5000
    else:
        year_score = max(0, int(5000 * max(0, 1 - (year_diff / 50) ** 1.5)))

    # Location scoring: exponential decay based on distance in km, 5000 max
    lat1, lon1 = math.radians(photo.latitude), math.radians(photo.longitude)
    lat2, lon2 = math.radians(guessed_lat), math.radians(guessed_lng)

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    distance_km = 6371 * c

    if distance_km < 1:
        location_score = 5000
    else:
        location_score = max(0, int(5000 * math.exp(-distance_km / 500)))

    total_score = year_score + location_score

    return jsonify({
        'year_score': year_score,
        'location_score': location_score,
        'total_score': total_score,
        'actual_year': photo.year,
        'actual_latitude': photo.latitude,
        'actual_longitude': photo.longitude,
        'actual_location_name': photo.location_name,
        'year_diff': year_diff,
        'distance_km': round(distance_km, 1),
    })

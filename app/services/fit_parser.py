import hashlib
from datetime import datetime, timezone
from fitparse import FitFile
from app import db
from app.models import Activity, ActivityLap, ActivityRecord, GpsPoint


class FitParser:
    """Service for parsing Garmin FIT files."""

    # Garmin semicircle to degrees conversion factor
    SEMICIRCLE_TO_DEGREES = 180.0 / (2 ** 31)

    # Sport type mapping
    SPORT_MAPPING = {
        'running': 'running',
        'cycling': 'cycling',
        'swimming': 'swimming',
        'walking': 'walking',
        'hiking': 'hiking',
        'fitness_equipment': 'gym',
        'training': 'training',
        'transition': 'transition',
        'all': 'multisport',
        'generic': 'other',
    }

    def __init__(self, file_path, filename=None):
        self.file_path = file_path
        self.filename = filename
        self.fit_file = None
        self.activity = None

    def parse(self):
        """Parse the FIT file and return an Activity object."""
        # Calculate file hash to detect duplicates
        file_hash = self._calculate_file_hash()

        # Check for duplicate
        existing = Activity.query.filter_by(file_hash=file_hash).first()
        if existing:
            return existing, False  # Return existing activity, not new

        # Parse the FIT file
        self.fit_file = FitFile(self.file_path)

        # Create activity
        self.activity = Activity(
            file_hash=file_hash,
            original_filename=self.filename
        )

        # Parse different message types
        self._parse_session_data()
        self._parse_lap_data()
        self._parse_record_data()

        # Add to database
        db.session.add(self.activity)
        db.session.commit()

        return self.activity, True  # Return new activity

    def _calculate_file_hash(self):
        """Calculate SHA-256 hash of the file."""
        sha256 = hashlib.sha256()
        with open(self.file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _convert_semicircles(self, semicircles):
        """Convert Garmin semicircles to degrees."""
        if semicircles is None:
            return None
        return semicircles * self.SEMICIRCLE_TO_DEGREES

    def _get_field_value(self, record, field_name, default=None):
        """Safely get a field value from a record."""
        try:
            value = record.get_value(field_name)
            return value if value is not None else default
        except (KeyError, AttributeError):
            return default

    def _parse_session_data(self):
        """Parse session messages for activity summary data."""
        for record in self.fit_file.get_messages('session'):
            # Sport type
            sport = self._get_field_value(record, 'sport', 'unknown')
            if isinstance(sport, str):
                self.activity.sport = self.SPORT_MAPPING.get(sport.lower(), sport.lower())
            else:
                self.activity.sport = str(sport) if sport else 'unknown'

            sub_sport = self._get_field_value(record, 'sub_sport')
            if sub_sport:
                self.activity.sub_sport = str(sub_sport)

            # Timing
            self.activity.start_time = self._get_field_value(record, 'start_time')
            self.activity.total_elapsed_time = self._get_field_value(record, 'total_elapsed_time')
            self.activity.total_timer_time = self._get_field_value(record, 'total_timer_time')

            if self.activity.start_time and self.activity.total_elapsed_time:
                from datetime import timedelta
                self.activity.end_time = self.activity.start_time + timedelta(
                    seconds=self.activity.total_elapsed_time
                )

            # Distance and speed
            self.activity.total_distance = self._get_field_value(record, 'total_distance')
            self.activity.avg_speed = self._get_field_value(record, 'avg_speed')
            self.activity.max_speed = self._get_field_value(record, 'max_speed')

            # Enhanced speed fields (if available)
            enhanced_avg = self._get_field_value(record, 'enhanced_avg_speed')
            enhanced_max = self._get_field_value(record, 'enhanced_max_speed')
            if enhanced_avg:
                self.activity.avg_speed = enhanced_avg
            if enhanced_max:
                self.activity.max_speed = enhanced_max

            # Heart rate
            self.activity.avg_heart_rate = self._get_field_value(record, 'avg_heart_rate')
            self.activity.max_heart_rate = self._get_field_value(record, 'max_heart_rate')

            # Cadence
            self.activity.avg_cadence = self._get_field_value(record, 'avg_cadence')
            self.activity.max_cadence = self._get_field_value(record, 'max_cadence')

            # Running cadence (steps per minute, needs to be doubled)
            avg_running_cadence = self._get_field_value(record, 'avg_running_cadence')
            max_running_cadence = self._get_field_value(record, 'max_running_cadence')
            if avg_running_cadence and self.activity.sport == 'running':
                self.activity.avg_cadence = avg_running_cadence * 2
            if max_running_cadence and self.activity.sport == 'running':
                self.activity.max_cadence = max_running_cadence * 2

            # Power
            self.activity.avg_power = self._get_field_value(record, 'avg_power')
            self.activity.max_power = self._get_field_value(record, 'max_power')
            self.activity.normalized_power = self._get_field_value(record, 'normalized_power')

            # Elevation
            self.activity.total_ascent = self._get_field_value(record, 'total_ascent')
            self.activity.total_descent = self._get_field_value(record, 'total_descent')

            # Calories
            self.activity.total_calories = self._get_field_value(record, 'total_calories')

            # Training metrics
            self.activity.training_stress_score = self._get_field_value(record, 'training_stress_score')
            self.activity.intensity_factor = self._get_field_value(record, 'intensity_factor')

            # GPS start position
            start_lat = self._get_field_value(record, 'start_position_lat')
            start_lng = self._get_field_value(record, 'start_position_long')
            self.activity.start_lat = self._convert_semicircles(start_lat)
            self.activity.start_lng = self._convert_semicircles(start_lng)

            # Only process first session
            break

        # If no session data, try to get from activity message
        if not self.activity.start_time:
            for record in self.fit_file.get_messages('activity'):
                self.activity.start_time = self._get_field_value(record, 'timestamp')
                break

    def _parse_lap_data(self):
        """Parse lap messages."""
        lap_number = 0
        for record in self.fit_file.get_messages('lap'):
            lap_number += 1

            lap = ActivityLap(
                lap_number=lap_number,
                start_time=self._get_field_value(record, 'start_time'),
                total_elapsed_time=self._get_field_value(record, 'total_elapsed_time'),
                total_timer_time=self._get_field_value(record, 'total_timer_time'),
                total_distance=self._get_field_value(record, 'total_distance'),
                avg_speed=self._get_field_value(record, 'avg_speed') or self._get_field_value(record, 'enhanced_avg_speed'),
                max_speed=self._get_field_value(record, 'max_speed') or self._get_field_value(record, 'enhanced_max_speed'),
                avg_heart_rate=self._get_field_value(record, 'avg_heart_rate'),
                max_heart_rate=self._get_field_value(record, 'max_heart_rate'),
                avg_cadence=self._get_field_value(record, 'avg_cadence'),
                max_cadence=self._get_field_value(record, 'max_cadence'),
                avg_power=self._get_field_value(record, 'avg_power'),
                max_power=self._get_field_value(record, 'max_power'),
                total_ascent=self._get_field_value(record, 'total_ascent'),
                total_descent=self._get_field_value(record, 'total_descent'),
                total_calories=self._get_field_value(record, 'total_calories'),
            )

            self.activity.laps.append(lap)

    def _parse_record_data(self):
        """Parse record messages for time-series data."""
        start_time = self.activity.start_time
        min_alt = None
        max_alt = None

        for record in self.fit_file.get_messages('record'):
            timestamp = self._get_field_value(record, 'timestamp')
            if not timestamp:
                continue

            # Calculate elapsed time
            elapsed_time = None
            if start_time and timestamp:
                elapsed_time = (timestamp - start_time).total_seconds()

            # Get position
            lat = self._convert_semicircles(self._get_field_value(record, 'position_lat'))
            lng = self._convert_semicircles(self._get_field_value(record, 'position_long'))

            # Get altitude
            altitude = self._get_field_value(record, 'altitude')
            enhanced_altitude = self._get_field_value(record, 'enhanced_altitude')
            if enhanced_altitude is not None:
                altitude = enhanced_altitude

            # Track min/max altitude
            if altitude is not None:
                if min_alt is None or altitude < min_alt:
                    min_alt = altitude
                if max_alt is None or altitude > max_alt:
                    max_alt = altitude

            # Create activity record
            activity_record = ActivityRecord(
                timestamp=timestamp,
                elapsed_time=elapsed_time,
                distance=self._get_field_value(record, 'distance'),
                heart_rate=self._get_field_value(record, 'heart_rate'),
                speed=self._get_field_value(record, 'speed') or self._get_field_value(record, 'enhanced_speed'),
                cadence=self._get_field_value(record, 'cadence'),
                power=self._get_field_value(record, 'power'),
                altitude=altitude,
                temperature=self._get_field_value(record, 'temperature'),
            )

            self.activity.records.append(activity_record)

            # Store GPS point if available
            if lat is not None and lng is not None:
                gps_point = GpsPoint(
                    timestamp=timestamp,
                    latitude=lat,
                    longitude=lng,
                    altitude=altitude,
                    elapsed_time=elapsed_time,
                )
                self.activity.gps_points.append(gps_point)

        # Update activity with min/max altitude
        self.activity.min_altitude = min_alt
        self.activity.max_altitude = max_alt

        # Update end position from last GPS point
        last_gps = self.activity.gps_points[-1] if self.activity.gps_points else None
        if last_gps:
            self.activity.end_lat = last_gps.latitude
            self.activity.end_lng = last_gps.longitude

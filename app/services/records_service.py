from datetime import datetime
from app import db
from app.models import Activity, ActivityRecord, PersonalRecord
from app.models.personal_record import STANDARD_DISTANCES


class RecordsService:
    """Service for tracking and managing personal records."""

    @staticmethod
    def check_and_update_records(activity):
        """Check if an activity has any new personal records."""
        new_records = []

        # Check distance-based records
        new_records.extend(RecordsService._check_distance_records(activity))

        # Check max values
        new_records.extend(RecordsService._check_max_records(activity))

        # Check longest activity
        new_records.extend(RecordsService._check_longest_records(activity))

        return new_records

    @staticmethod
    def _check_distance_records(activity):
        """Check for personal records at standard distances."""
        new_records = []
        sport = activity.sport

        if sport not in STANDARD_DISTANCES:
            return new_records

        # Get all records for this activity, ordered by elapsed time
        records = ActivityRecord.query.filter_by(activity_id=activity.id).order_by(
            ActivityRecord.elapsed_time
        ).all()

        if not records:
            return new_records

        for record_name, distance_m in STANDARD_DISTANCES[sport]:
            # Check if activity is long enough
            if not activity.total_distance or activity.total_distance < distance_m:
                continue

            # Find time to complete this distance
            time_for_distance = RecordsService._find_best_time_for_distance(
                records, distance_m
            )

            if time_for_distance is None:
                continue

            # Check if this is a new record
            existing_record = PersonalRecord.query.filter_by(
                sport=sport,
                record_type='distance',
                record_name=record_name
            ).first()

            is_new_record = False
            if existing_record is None:
                is_new_record = True
            elif time_for_distance < existing_record.value:
                is_new_record = True
                db.session.delete(existing_record)

            if is_new_record:
                new_record = PersonalRecord(
                    activity_id=activity.id,
                    sport=sport,
                    record_type='distance',
                    record_name=record_name,
                    value=time_for_distance,
                    unit='seconds',
                    achieved_at=activity.start_time
                )
                db.session.add(new_record)
                new_records.append(new_record)

        db.session.commit()
        return new_records

    @staticmethod
    def _find_best_time_for_distance(records, target_distance):
        """Find the fastest time to cover a specific distance using sliding window."""
        if not records:
            return None

        best_time = None

        # We need to find the minimum time to cover target_distance
        # Using a sliding window approach
        for i, start_record in enumerate(records):
            if start_record.distance is None:
                continue

            start_distance = start_record.distance
            start_time = start_record.elapsed_time or 0

            for end_record in records[i:]:
                if end_record.distance is None:
                    continue

                segment_distance = end_record.distance - start_distance
                if segment_distance >= target_distance:
                    segment_time = (end_record.elapsed_time or 0) - start_time

                    # Interpolate to get exact time for target distance
                    if segment_distance > 0:
                        ratio = target_distance / segment_distance
                        interpolated_time = segment_time * ratio

                        if best_time is None or interpolated_time < best_time:
                            best_time = interpolated_time

                    break

        return best_time

    @staticmethod
    def _check_max_records(activity):
        """Check for max heart rate, speed, power records."""
        new_records = []
        sport = activity.sport

        # Max heart rate
        if activity.max_heart_rate:
            new_records.extend(RecordsService._update_max_record(
                activity, 'max_heart_rate', 'Max Heart Rate',
                activity.max_heart_rate, 'bpm'
            ))

        # Max speed
        if activity.max_speed:
            new_records.extend(RecordsService._update_max_record(
                activity, 'max_speed', 'Max Speed',
                activity.max_speed, 'm/s'
            ))

        # Max power (cycling)
        if activity.max_power:
            new_records.extend(RecordsService._update_max_record(
                activity, 'max_power', 'Max Power',
                activity.max_power, 'watts'
            ))

        return new_records

    @staticmethod
    def _update_max_record(activity, record_type, record_name, value, unit):
        """Update a max value record if the new value is higher."""
        new_records = []
        sport = activity.sport

        existing = PersonalRecord.query.filter_by(
            sport=sport,
            record_type=record_type,
            record_name=record_name
        ).first()

        is_new_record = False
        if existing is None:
            is_new_record = True
        elif value > existing.value:
            is_new_record = True
            db.session.delete(existing)

        if is_new_record:
            new_record = PersonalRecord(
                activity_id=activity.id,
                sport=sport,
                record_type=record_type,
                record_name=record_name,
                value=value,
                unit=unit,
                achieved_at=activity.start_time
            )
            db.session.add(new_record)
            db.session.commit()
            new_records.append(new_record)

        return new_records

    @staticmethod
    def _check_longest_records(activity):
        """Check for longest distance and duration records."""
        new_records = []
        sport = activity.sport

        # Longest distance
        if activity.total_distance:
            existing = PersonalRecord.query.filter_by(
                sport=sport,
                record_type='longest',
                record_name='Longest Distance'
            ).first()

            is_new_record = False
            if existing is None:
                is_new_record = True
            elif activity.total_distance > existing.value:
                is_new_record = True
                db.session.delete(existing)

            if is_new_record:
                new_record = PersonalRecord(
                    activity_id=activity.id,
                    sport=sport,
                    record_type='longest',
                    record_name='Longest Distance',
                    value=activity.total_distance,
                    unit='meters',
                    achieved_at=activity.start_time
                )
                db.session.add(new_record)
                new_records.append(new_record)

        # Longest duration
        if activity.total_timer_time:
            existing = PersonalRecord.query.filter_by(
                sport=sport,
                record_type='longest',
                record_name='Longest Duration'
            ).first()

            is_new_record = False
            if existing is None:
                is_new_record = True
            elif activity.total_timer_time > existing.value:
                is_new_record = True
                db.session.delete(existing)

            if is_new_record:
                new_record = PersonalRecord(
                    activity_id=activity.id,
                    sport=sport,
                    record_type='longest',
                    record_name='Longest Duration',
                    value=activity.total_timer_time,
                    unit='seconds',
                    achieved_at=activity.start_time
                )
                db.session.add(new_record)
                new_records.append(new_record)

        # Most elevation gain
        if activity.total_ascent:
            existing = PersonalRecord.query.filter_by(
                sport=sport,
                record_type='longest',
                record_name='Most Elevation Gain'
            ).first()

            is_new_record = False
            if existing is None:
                is_new_record = True
            elif activity.total_ascent > existing.value:
                is_new_record = True
                db.session.delete(existing)

            if is_new_record:
                new_record = PersonalRecord(
                    activity_id=activity.id,
                    sport=sport,
                    record_type='longest',
                    record_name='Most Elevation Gain',
                    value=activity.total_ascent,
                    unit='meters',
                    achieved_at=activity.start_time
                )
                db.session.add(new_record)
                new_records.append(new_record)

        db.session.commit()
        return new_records

    @staticmethod
    def get_all_records(sport=None):
        """Get all personal records, optionally filtered by sport."""
        query = PersonalRecord.query

        if sport:
            query = query.filter_by(sport=sport)

        records = query.order_by(
            PersonalRecord.sport,
            PersonalRecord.record_type,
            PersonalRecord.record_name
        ).all()

        # Group by sport and type
        grouped = {}
        for record in records:
            if record.sport not in grouped:
                grouped[record.sport] = {}
            if record.record_type not in grouped[record.sport]:
                grouped[record.sport][record.record_type] = []
            grouped[record.sport][record.record_type].append(record.to_dict())

        return grouped

    @staticmethod
    def get_records_for_activity(activity_id):
        """Get all personal records achieved in a specific activity."""
        records = PersonalRecord.query.filter_by(activity_id=activity_id).all()
        return [record.to_dict() for record in records]

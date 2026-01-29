from datetime import datetime, timedelta
from sqlalchemy import func, extract
from app import db
from app.models import Activity


class StatsService:
    """Service for calculating activity statistics and summaries."""

    @staticmethod
    def get_weekly_summary(year=None, week=None):
        """Get summary statistics for a specific week."""
        if year is None:
            year = datetime.now().year
        if week is None:
            week = datetime.now().isocalendar()[1]

        # Calculate start and end of week
        first_day_of_year = datetime(year, 1, 1)
        first_monday = first_day_of_year + timedelta(days=(7 - first_day_of_year.weekday()) % 7)
        if first_day_of_year.weekday() == 0:  # If Jan 1 is Monday
            first_monday = first_day_of_year

        week_start = first_monday + timedelta(weeks=week - 1)
        week_end = week_start + timedelta(days=7)

        return StatsService._get_summary_for_period(week_start, week_end, 'week')

    @staticmethod
    def get_monthly_summary(year=None, month=None):
        """Get summary statistics for a specific month."""
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month

        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1)
        else:
            month_end = datetime(year, month + 1, 1)

        return StatsService._get_summary_for_period(month_start, month_end, 'month')

    @staticmethod
    def get_annual_summary(year=None):
        """Get summary statistics for a specific year."""
        if year is None:
            year = datetime.now().year

        year_start = datetime(year, 1, 1)
        year_end = datetime(year + 1, 1, 1)

        return StatsService._get_summary_for_period(year_start, year_end, 'year')

    @staticmethod
    def _get_summary_for_period(start_date, end_date, period_type):
        """Calculate summary statistics for a date range."""
        activities = Activity.query.filter(
            Activity.start_time >= start_date,
            Activity.start_time < end_date
        ).all()

        if not activities:
            return {
                'period_type': period_type,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_activities': 0,
                'total_distance': 0,
                'total_duration': 0,
                'total_calories': 0,
                'total_elevation': 0,
                'by_sport': {},
            }

        # Calculate totals
        total_distance = sum(a.total_distance or 0 for a in activities)
        total_duration = sum(a.total_timer_time or 0 for a in activities)
        total_calories = sum(a.total_calories or 0 for a in activities)
        total_elevation = sum(a.total_ascent or 0 for a in activities)

        # Group by sport
        by_sport = {}
        for activity in activities:
            sport = activity.sport
            if sport not in by_sport:
                by_sport[sport] = {
                    'count': 0,
                    'distance': 0,
                    'duration': 0,
                    'calories': 0,
                    'elevation': 0,
                    'avg_heart_rate': [],
                }
            by_sport[sport]['count'] += 1
            by_sport[sport]['distance'] += activity.total_distance or 0
            by_sport[sport]['duration'] += activity.total_timer_time or 0
            by_sport[sport]['calories'] += activity.total_calories or 0
            by_sport[sport]['elevation'] += activity.total_ascent or 0
            if activity.avg_heart_rate:
                by_sport[sport]['avg_heart_rate'].append(activity.avg_heart_rate)

        # Calculate averages
        for sport in by_sport:
            hr_list = by_sport[sport]['avg_heart_rate']
            by_sport[sport]['avg_heart_rate'] = (
                sum(hr_list) / len(hr_list) if hr_list else None
            )

        return {
            'period_type': period_type,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_activities': len(activities),
            'total_distance': total_distance,
            'total_distance_km': total_distance / 1000,
            'total_duration': total_duration,
            'total_duration_hours': total_duration / 3600,
            'total_calories': total_calories,
            'total_elevation': total_elevation,
            'by_sport': by_sport,
        }

    @staticmethod
    def get_all_time_stats():
        """Get all-time statistics."""
        activities = Activity.query.all()

        if not activities:
            return {
                'total_activities': 0,
                'total_distance': 0,
                'total_duration': 0,
                'first_activity': None,
                'last_activity': None,
            }

        total_distance = sum(a.total_distance or 0 for a in activities)
        total_duration = sum(a.total_timer_time or 0 for a in activities)
        total_calories = sum(a.total_calories or 0 for a in activities)
        total_elevation = sum(a.total_ascent or 0 for a in activities)

        activities_sorted = sorted(activities, key=lambda x: x.start_time or datetime.min)

        return {
            'total_activities': len(activities),
            'total_distance': total_distance,
            'total_distance_km': total_distance / 1000,
            'total_duration': total_duration,
            'total_duration_hours': total_duration / 3600,
            'total_calories': total_calories,
            'total_elevation': total_elevation,
            'first_activity': activities_sorted[0].start_time.isoformat() if activities_sorted else None,
            'last_activity': activities_sorted[-1].start_time.isoformat() if activities_sorted else None,
        }

    @staticmethod
    def get_yearly_comparison(years=None):
        """Compare statistics across multiple years."""
        if years is None:
            current_year = datetime.now().year
            years = list(range(current_year - 4, current_year + 1))

        comparison = []
        for year in years:
            summary = StatsService.get_annual_summary(year)
            summary['year'] = year
            comparison.append(summary)

        return comparison

    @staticmethod
    def get_monthly_trend(year=None):
        """Get monthly statistics for a year."""
        if year is None:
            year = datetime.now().year

        months = []
        for month in range(1, 13):
            summary = StatsService.get_monthly_summary(year, month)
            summary['month'] = month
            summary['month_name'] = datetime(year, month, 1).strftime('%B')
            months.append(summary)

        return {
            'year': year,
            'months': months,
        }

    @staticmethod
    def get_activity_heatmap_data(year=None):
        """Get daily activity counts for heatmap visualization."""
        if year is None:
            year = datetime.now().year

        year_start = datetime(year, 1, 1)
        year_end = datetime(year + 1, 1, 1)

        activities = Activity.query.filter(
            Activity.start_time >= year_start,
            Activity.start_time < year_end
        ).all()

        # Group by date
        heatmap = {}
        for activity in activities:
            date_key = activity.start_time.strftime('%Y-%m-%d')
            if date_key not in heatmap:
                heatmap[date_key] = {
                    'count': 0,
                    'distance': 0,
                    'duration': 0,
                }
            heatmap[date_key]['count'] += 1
            heatmap[date_key]['distance'] += activity.total_distance or 0
            heatmap[date_key]['duration'] += activity.total_timer_time or 0

        return {
            'year': year,
            'data': heatmap,
        }

#!/usr/bin/env python3
"""
Garmin Activity Tracker - Main Entry Point

A Strava-like application for tracking and analyzing Garmin fitness data.
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# Garmin Activity Tracker

A Strava-like web application for tracking and analyzing your Garmin fitness data. Upload your FIT files and get comprehensive insights into your workouts with interactive charts, maps, and statistics.

## Features

- **FIT File Upload**: Upload single or multiple Garmin FIT files
- **Activity Dashboard**: View recent activities with key metrics
- **Activity Details**:
  - Interactive GPS route maps (Leaflet)
  - Heart rate, speed, elevation, and cadence charts
  - Lap-by-lap breakdown
- **Statistics & Summaries**:
  - Weekly, monthly, and annual statistics
  - Year-over-year comparisons
  - Activity heatmap calendar
  - Sport-specific breakdowns
- **Personal Records**: Automatic tracking of PRs for various distances and metrics
- **Activity Comparison**: Compare up to 4 activities side-by-side with overlaid charts and maps

## Tech Stack

- **Backend**: Python/Flask
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, JavaScript
- **Charts**: Chart.js
- **Maps**: Leaflet with OpenStreetMap
- **FIT Parsing**: fitparse library

## Installation

### Prerequisites

- Python 3.9+
- PostgreSQL database
- pip (Python package manager)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd garmin-activity-tracker
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Create the database**
   ```bash
   createdb garmin_tracker  # or use your PostgreSQL client
   ```

6. **Run the application**
   ```bash
   python run.py
   ```

7. **Open in browser**
   ```
   http://localhost:5000
   ```

## Cloud Deployment

### Heroku

1. Create a Heroku app
2. Add PostgreSQL addon: `heroku addons:create heroku-postgresql:hobby-dev`
3. Set environment variables
4. Deploy: `git push heroku main`

### Railway / Render

1. Connect your GitHub repository
2. Add PostgreSQL service
3. Set `DATABASE_URL` environment variable
4. Deploy

## Usage

### Uploading Activities

1. Export FIT files from Garmin Connect:
   - Go to connect.garmin.com
   - Navigate to Activities
   - Click on an activity
   - Click the gear icon → Export Original

2. Or copy FIT files directly from your Garmin device (GARMIN/ACTIVITY folder)

3. Drag and drop files on the Upload page, or click to browse

### Viewing Statistics

- **Dashboard**: Overview of all-time stats and recent activities
- **Stats Page**: Detailed weekly/monthly/annual breakdowns with charts
- **Records Page**: View all personal records by sport

### Comparing Activities

1. Go to Compare page
2. Select 2-4 activities (optionally filter by sport)
3. Click "Compare Selected"
4. View side-by-side metrics, overlaid charts, and route maps

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/activities` | GET | List activities (with pagination/filters) |
| `/api/activities/<id>` | GET | Get activity details |
| `/api/activities/<id>` | DELETE | Delete an activity |
| `/api/activities/<id>` | PATCH | Update activity name |
| `/api/upload` | POST | Upload single FIT file |
| `/api/upload/batch` | POST | Upload multiple FIT files |
| `/api/stats/summary` | GET | Get all-time statistics |
| `/api/stats/weekly` | GET | Get weekly statistics |
| `/api/stats/monthly` | GET | Get monthly statistics |
| `/api/stats/annual` | GET | Get annual statistics |
| `/api/records` | GET | Get personal records |
| `/api/compare` | GET | Compare multiple activities |
| `/api/sports` | GET | List sports with activity counts |

## Project Structure

```
garmin-activity-tracker/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models/              # Database models
│   │   ├── activity.py      # Activity, Lap, Record, GPS models
│   │   └── personal_record.py
│   ├── routes/              # API and view routes
│   │   ├── api.py           # REST API endpoints
│   │   └── main.py          # HTML page routes
│   ├── services/            # Business logic
│   │   ├── fit_parser.py    # FIT file parsing
│   │   ├── stats_service.py # Statistics calculations
│   │   └── records_service.py # Personal records tracking
│   ├── static/
│   │   ├── css/style.css    # Styles
│   │   └── js/              # JavaScript modules
│   └── templates/           # Jinja2 HTML templates
├── uploads/                 # Temporary upload folder
├── requirements.txt         # Python dependencies
├── run.py                   # Application entry point
├── Procfile                 # Heroku deployment
└── README.md
```

## Supported Metrics

- Distance, Duration, Pace/Speed
- Heart Rate (avg, max)
- Cadence (running, cycling)
- Power (cycling)
- Elevation (gain, loss, min, max)
- Calories
- GPS coordinates for mapping

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - feel free to use this for personal or commercial projects.

# NFL GeoGuessr

A TimeGuessr-inspired game for NFL history. View historic NFL photos and guess **where** the game was played (drop a pin on the map) and **when** the photo was taken (pick the year). The closer your guesses, the more points you earn.

## How It Works

1. **5 rounds per game** — each round shows a random NFL history photo
2. **Drop a pin** on the map to guess the game location (up to 5,000 points)
3. **Slide the year** to guess when the photo was taken (up to 5,000 points)
4. **Max score: 50,000** (10,000 per round)

Scoring uses exponential curves — near-perfect guesses earn massively more points than "close enough" ones.

## Features

- Upload NFL photos with year, location, and description metadata
- Interactive Leaflet map for both guessing and uploading
- Animated round-by-round results with distance and year diff
- Results map showing your guess vs. actual location
- Final score breakdown
- Dark theme UI
- Responsive (works on mobile)

## Tech Stack

- **Backend**: Python / Flask
- **Database**: SQLite (default) or PostgreSQL
- **Frontend**: HTML5, CSS3, vanilla JavaScript
- **Maps**: Leaflet with OpenStreetMap

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Run
python run.py
```

Then open http://localhost:5000

## Adding Photos

1. Go to `/upload`
2. Drop or browse for an NFL image
3. Enter the year, stadium/location name, and click the map to set coordinates
4. Upload — the photo is now in the game pool

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/photos` | GET | List all photos |
| `/api/photos` | POST | Upload a new photo |
| `/api/photos/<id>` | DELETE | Delete a photo |
| `/api/game/new` | GET | Start new game (5 random photos) |
| `/api/game/score` | POST | Submit a guess, get score |

## Project Structure

```
nfl-geoguessr/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models/
│   │   └── photo.py         # Photo model
│   ├── routes/
│   │   ├── api.py           # REST API + game endpoints
│   │   └── main.py          # Page routes
│   ├── static/
│   │   ├── css/style.css    # Dark theme styles
│   │   └── js/
│   │       ├── game.js      # Game logic (map, slider, scoring)
│   │       └── upload.js    # Upload page logic
│   └── templates/
│       ├── base.html        # Base layout
│       ├── index.html       # Landing page
│       ├── play.html        # Game page
│       └── upload.html      # Photo upload page
├── uploads/                 # Uploaded photos
├── requirements.txt
├── run.py
└── Procfile
```

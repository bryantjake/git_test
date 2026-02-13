document.addEventListener('DOMContentLoaded', () => {
    const loadingScreen = document.getElementById('loading-screen');
    const noPhotosScreen = document.getElementById('no-photos-screen');
    const gameScreen = document.getElementById('game-screen');
    const roundResults = document.getElementById('round-results');
    const finalResults = document.getElementById('final-results');

    let gameData = null;
    let currentRound = 0;
    let totalScore = 0;
    let roundScores = [];
    let gameMap = null;
    let guessMarker = null;
    let hasPlacedPin = false;
    let resultMap = null;

    // Start new game
    async function startGame() {
        loadingScreen.style.display = 'flex';
        noPhotosScreen.style.display = 'none';
        gameScreen.style.display = 'none';
        roundResults.style.display = 'none';
        finalResults.style.display = 'none';

        try {
            const res = await fetch('/api/game/new');
            const data = await res.json();

            if (!res.ok) {
                loadingScreen.style.display = 'none';
                noPhotosScreen.style.display = 'flex';
                return;
            }

            gameData = data;
            currentRound = 0;
            totalScore = 0;
            roundScores = [];

            document.getElementById('total-rounds').textContent = gameData.rounds;
            document.getElementById('total-score').textContent = '0';

            loadingScreen.style.display = 'none';
            gameScreen.style.display = 'block';

            initMap();
            loadRound();
        } catch (err) {
            loadingScreen.style.display = 'none';
            noPhotosScreen.style.display = 'flex';
        }
    }

    function initMap() {
        if (gameMap) {
            gameMap.remove();
        }

        gameMap = L.map('game-map', {
            center: [39.8283, -98.5795],
            zoom: 4,
            zoomControl: true,
        });

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 19,
        }).addTo(gameMap);

        gameMap.on('click', (e) => {
            placeGuess(e.latlng.lat, e.latlng.lng);
        });

        // Fix map size after display
        setTimeout(() => gameMap.invalidateSize(), 100);
    }

    function placeGuess(lat, lng) {
        if (guessMarker) {
            guessMarker.setLatLng([lat, lng]);
        } else {
            guessMarker = L.marker([lat, lng], {
                icon: L.divIcon({
                    className: 'guess-marker',
                    html: '<div style="width:20px;height:20px;background:#448aff;border:3px solid white;border-radius:50%;box-shadow:0 0 10px rgba(68,138,255,0.5);"></div>',
                    iconSize: [20, 20],
                    iconAnchor: [10, 10],
                }),
            }).addTo(gameMap);
        }

        hasPlacedPin = true;
        document.getElementById('map-hint').textContent =
            `Selected: ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
        document.getElementById('submit-guess').disabled = false;
    }

    function loadRound() {
        const photo = gameData.photos[currentRound];

        // Update round display
        document.getElementById('current-round').textContent = currentRound + 1;

        // Load photo
        const img = document.getElementById('game-photo');
        img.src = `/api/photos/file/${photo.filename}`;

        // Show description if present
        const descEl = document.getElementById('photo-description');
        if (photo.description) {
            descEl.textContent = photo.description;
            descEl.style.display = 'block';
        } else {
            descEl.style.display = 'none';
        }

        // Reset year slider
        const slider = document.getElementById('year-slider');
        slider.value = 1970;
        document.getElementById('year-value').textContent = '1970';

        // Reset map pin
        if (guessMarker) {
            gameMap.removeLayer(guessMarker);
            guessMarker = null;
        }
        hasPlacedPin = false;
        document.getElementById('map-hint').textContent = 'Click on the map to place your guess';
        document.getElementById('submit-guess').disabled = true;

        // Reset map view
        gameMap.setView([39.8283, -98.5795], 4);
        setTimeout(() => gameMap.invalidateSize(), 50);
    }

    // Year slider
    document.getElementById('year-slider').addEventListener('input', (e) => {
        document.getElementById('year-value').textContent = e.target.value;
    });

    // Submit guess
    document.getElementById('submit-guess').addEventListener('click', async () => {
        if (!hasPlacedPin) return;

        const photo = gameData.photos[currentRound];
        const guessedYear = parseInt(document.getElementById('year-slider').value);
        const latlng = guessMarker.getLatLng();

        const res = await fetch('/api/game/score', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                photo_id: photo.id,
                year: guessedYear,
                latitude: latlng.lat,
                longitude: latlng.lng,
            }),
        });

        const result = await res.json();

        totalScore += result.total_score;
        roundScores.push(result);

        document.getElementById('total-score').textContent = totalScore.toLocaleString();

        showRoundResults(result, latlng);
    });

    function showRoundResults(result, guessLatLng) {
        roundResults.style.display = 'flex';

        document.getElementById('result-round').textContent = currentRound + 1;
        document.getElementById('result-location-score').textContent =
            result.location_score.toLocaleString();
        document.getElementById('result-year-score').textContent =
            result.year_score.toLocaleString();
        document.getElementById('result-total-score').textContent =
            result.total_score.toLocaleString();

        document.getElementById('result-distance').textContent =
            `${result.distance_km} km away`;
        document.getElementById('result-year-diff').textContent =
            result.year_diff === 0 ? 'Exact!' : `${result.year_diff} year${result.year_diff > 1 ? 's' : ''} off`;

        document.getElementById('result-actual-location').textContent =
            result.actual_location_name || `${result.actual_latitude.toFixed(4)}, ${result.actual_longitude.toFixed(4)}`;
        document.getElementById('result-actual-year').textContent = result.actual_year;

        // Animate bars
        setTimeout(() => {
            document.getElementById('location-bar').style.width =
                `${(result.location_score / 5000) * 100}%`;
            document.getElementById('year-bar').style.width =
                `${(result.year_score / 5000) * 100}%`;
        }, 100);

        // Update button text for last round
        const nextBtn = document.getElementById('next-round');
        nextBtn.textContent = currentRound + 1 >= gameData.rounds ? 'See Final Score' : 'Next Round';

        // Show result map
        if (resultMap) {
            resultMap.remove();
        }

        resultMap = L.map('result-map', {
            zoomControl: false,
            attributionControl: false,
        });

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
        }).addTo(resultMap);

        // Guess marker (blue)
        L.marker([guessLatLng.lat, guessLatLng.lng], {
            icon: L.divIcon({
                className: 'guess-marker',
                html: '<div style="width:16px;height:16px;background:#448aff;border:3px solid white;border-radius:50%;"></div>',
                iconSize: [16, 16],
                iconAnchor: [8, 8],
            }),
        }).addTo(resultMap);

        // Actual marker (green)
        L.marker([result.actual_latitude, result.actual_longitude], {
            icon: L.divIcon({
                className: 'actual-marker',
                html: '<div style="width:16px;height:16px;background:#00e676;border:3px solid white;border-radius:50%;"></div>',
                iconSize: [16, 16],
                iconAnchor: [8, 8],
            }),
        }).addTo(resultMap);

        // Line between the two
        L.polyline(
            [[guessLatLng.lat, guessLatLng.lng], [result.actual_latitude, result.actual_longitude]],
            { color: '#ff5252', weight: 2, dashArray: '6 4' }
        ).addTo(resultMap);

        // Fit both markers
        const bounds = L.latLngBounds(
            [guessLatLng.lat, guessLatLng.lng],
            [result.actual_latitude, result.actual_longitude]
        );
        resultMap.fitBounds(bounds, { padding: [30, 30] });
    }

    // Next round
    document.getElementById('next-round').addEventListener('click', () => {
        roundResults.style.display = 'none';

        // Reset bars
        document.getElementById('location-bar').style.width = '0%';
        document.getElementById('year-bar').style.width = '0%';

        currentRound++;

        if (currentRound >= gameData.rounds) {
            showFinalResults();
        } else {
            loadRound();
        }
    });

    function showFinalResults() {
        gameScreen.style.display = 'none';
        finalResults.style.display = 'flex';

        const maxScore = gameData.rounds * 10000;
        document.getElementById('final-score').textContent = totalScore.toLocaleString();
        document.querySelector('.final-score-max').textContent = `/ ${maxScore.toLocaleString()}`;

        // Build breakdown
        const breakdown = document.getElementById('final-breakdown');
        breakdown.innerHTML = '';

        roundScores.forEach((score, i) => {
            const row = document.createElement('div');
            row.className = 'final-round-row';
            row.innerHTML = `
                <span>Round ${i + 1}</span>
                <span class="final-round-score">${score.total_score.toLocaleString()} pts</span>
            `;
            breakdown.appendChild(row);
        });
    }

    // Play again
    document.getElementById('play-again').addEventListener('click', () => {
        startGame();
    });

    // Start
    startGame();
});

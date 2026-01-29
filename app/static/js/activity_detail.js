/**
 * Activity detail page functionality
 */

let activityData = null;
let map = null;

document.addEventListener('DOMContentLoaded', async () => {
    await loadActivityData();
    setupEventListeners();
});

// Load activity data
async function loadActivityData() {
    try {
        activityData = await API.getActivity(ACTIVITY_ID);

        // Format duration
        const durationEl = document.getElementById('duration-value');
        durationEl.textContent = formatDuration(activityData.total_timer_time);

        // Format pace/speed
        const paceEl = document.getElementById('pace-value');
        if (activityData.sport === 'cycling') {
            paceEl.textContent = formatSpeed(activityData.avg_speed);
        } else {
            paceEl.textContent = formatPace(activityData.avg_speed);
        }

        // Load map if GPS data available
        if (activityData.gps_points && activityData.gps_points.length > 0) {
            initMap();
        } else {
            document.querySelector('.map-card').innerHTML = '<p class="no-data">No GPS data available</p>';
        }

        // Load charts
        if (activityData.records && activityData.records.length > 0) {
            loadCharts();
        }

        // Load laps
        if (activityData.laps && activityData.laps.length > 0) {
            loadLapsTable();
        }

        // Check for personal records
        await loadActivityRecords();

    } catch (error) {
        console.error('Failed to load activity:', error);
        showNotification('Failed to load activity data', 'error');
    }
}

// Initialize map with route
function initMap() {
    const points = activityData.gps_points;
    if (!points || points.length === 0) return;

    // Calculate center
    const latSum = points.reduce((sum, p) => sum + p.lat, 0);
    const lngSum = points.reduce((sum, p) => sum + p.lng, 0);
    const center = [latSum / points.length, lngSum / points.length];

    // Initialize map
    map = L.map('activity-map').setView(center, 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    // Create route polyline
    const routeCoords = points.map(p => [p.lat, p.lng]);
    const route = L.polyline(routeCoords, {
        color: getSportColor(activityData.sport),
        weight: 4,
        opacity: 0.8
    }).addTo(map);

    // Add start and end markers
    if (points.length > 0) {
        L.circleMarker([points[0].lat, points[0].lng], {
            radius: 8,
            fillColor: '#00b894',
            color: '#fff',
            weight: 2,
            fillOpacity: 1
        }).addTo(map).bindPopup('Start');

        L.circleMarker([points[points.length - 1].lat, points[points.length - 1].lng], {
            radius: 8,
            fillColor: '#d63031',
            color: '#fff',
            weight: 2,
            fillOpacity: 1
        }).addTo(map).bindPopup('Finish');
    }

    // Fit map to route
    map.fitBounds(route.getBounds(), { padding: [20, 20] });
}

// Load all charts
function loadCharts() {
    const records = activityData.records;

    // Prepare data
    const labels = records.map(r => formatDuration(r.elapsed_time));
    const hrData = records.map(r => r.heart_rate).filter(v => v !== null);
    const speedData = records.map(r => r.speed ? r.speed * 3.6 : null);
    const elevationData = records.map(r => r.altitude);
    const cadenceData = records.map(r => r.cadence);

    // Heart rate chart
    if (hrData.some(v => v !== null)) {
        createChart('hr-chart', labels, hrData, 'Heart Rate (bpm)', '#d63031');
    } else {
        document.getElementById('hr-chart').parentElement.innerHTML = '<h3>Heart Rate</h3><p class="no-data">No heart rate data</p>';
    }

    // Speed chart
    if (speedData.some(v => v !== null)) {
        createChart('speed-chart', labels, speedData, 'Speed (km/h)', '#0984e3');
    } else {
        document.getElementById('speed-chart').parentElement.innerHTML = '<h3>Speed / Pace</h3><p class="no-data">No speed data</p>';
    }

    // Elevation chart
    if (elevationData.some(v => v !== null)) {
        createAreaChart('elevation-chart', labels, elevationData, 'Elevation (m)', '#6c5ce7');
    } else {
        document.getElementById('elevation-chart').parentElement.innerHTML = '<h3>Elevation</h3><p class="no-data">No elevation data</p>';
    }

    // Cadence chart
    if (cadenceData.some(v => v !== null)) {
        createChart('cadence-chart', labels, cadenceData, 'Cadence', '#00cec9');
    } else {
        document.getElementById('cadence-chart').parentElement.innerHTML = '<h3>Cadence</h3><p class="no-data">No cadence data</p>';
    }
}

// Create a line chart
function createChart(canvasId, labels, data, label, color) {
    const ctx = document.getElementById(canvasId).getContext('2d');

    // Sample data if too many points
    const sampleRate = Math.ceil(data.length / 500);
    const sampledLabels = labels.filter((_, i) => i % sampleRate === 0);
    const sampledData = data.filter((_, i) => i % sampleRate === 0);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: sampledLabels,
            datasets: [{
                label: label,
                data: sampledData,
                borderColor: color,
                backgroundColor: 'transparent',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    display: false
                },
                y: {
                    beginAtZero: false,
                    grid: { color: '#f0f0f0' }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

// Create an area chart (for elevation)
function createAreaChart(canvasId, labels, data, label, color) {
    const ctx = document.getElementById(canvasId).getContext('2d');

    // Sample data if too many points
    const sampleRate = Math.ceil(data.length / 500);
    const sampledLabels = labels.filter((_, i) => i % sampleRate === 0);
    const sampledData = data.filter((_, i) => i % sampleRate === 0);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: sampledLabels,
            datasets: [{
                label: label,
                data: sampledData,
                borderColor: color,
                backgroundColor: color + '40',
                borderWidth: 2,
                pointRadius: 0,
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    display: false
                },
                y: {
                    beginAtZero: false,
                    grid: { color: '#f0f0f0' }
                }
            }
        }
    });
}

// Load laps table
function loadLapsTable() {
    const tbody = document.querySelector('#laps-table tbody');
    const laps = activityData.laps;

    tbody.innerHTML = laps.map(lap => `
        <tr>
            <td>${lap.lap_number}</td>
            <td>${formatDistance(lap.total_distance)}</td>
            <td>${formatDuration(lap.total_timer_time)}</td>
            <td>${activityData.sport === 'cycling' ? formatSpeed(lap.avg_speed) : formatPace(lap.avg_speed)}</td>
            <td>${lap.avg_heart_rate || '-'}</td>
            <td>${lap.max_heart_rate || '-'}</td>
            <td>${lap.total_ascent ? lap.total_ascent.toFixed(0) + ' m' : '-'}</td>
            <td>${lap.total_calories || '-'}</td>
        </tr>
    `).join('');
}

// Load personal records achieved in this activity
async function loadActivityRecords() {
    try {
        const records = await API.getActivityRecords(ACTIVITY_ID);

        if (records.length > 0) {
            const banner = document.getElementById('records-banner');
            const list = document.getElementById('activity-records');

            list.innerHTML = records.map(r => `
                <div class="record-badge">
                    <strong>${r.record_name}</strong>: ${r.formatted_value}
                </div>
            `).join('');

            banner.style.display = 'block';
        }
    } catch (error) {
        console.error('Failed to load activity records:', error);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Edit name button
    document.getElementById('edit-name-btn').addEventListener('click', () => {
        const modal = document.getElementById('edit-modal');
        const input = document.getElementById('new-name-input');
        input.value = activityData.name;
        modal.style.display = 'flex';
    });

    // Cancel edit
    document.getElementById('cancel-edit').addEventListener('click', () => {
        document.getElementById('edit-modal').style.display = 'none';
    });

    // Save name
    document.getElementById('save-name').addEventListener('click', async () => {
        const newName = document.getElementById('new-name-input').value.trim();
        if (!newName) return;

        try {
            await API.updateActivity(ACTIVITY_ID, { name: newName });
            document.getElementById('activity-name').textContent = newName;
            document.getElementById('edit-modal').style.display = 'none';
            showNotification('Activity name updated', 'success');
        } catch (error) {
            showNotification('Failed to update name', 'error');
        }
    });

    // Delete button
    document.getElementById('delete-btn').addEventListener('click', async () => {
        if (!confirm('Are you sure you want to delete this activity? This cannot be undone.')) {
            return;
        }

        try {
            await API.deleteActivity(ACTIVITY_ID);
            showNotification('Activity deleted', 'success');
            setTimeout(() => {
                window.location.href = '/activities';
            }, 1000);
        } catch (error) {
            showNotification('Failed to delete activity', 'error');
        }
    });

    // Close modal on outside click
    document.getElementById('edit-modal').addEventListener('click', (e) => {
        if (e.target.id === 'edit-modal') {
            e.target.style.display = 'none';
        }
    });
}

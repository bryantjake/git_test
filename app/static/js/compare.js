/**
 * Activity Comparison page functionality
 */

let selectedActivities = [];
let allActivities = [];
let compareMap = null;

document.addEventListener('DOMContentLoaded', async () => {
    await loadSportFilter();
    await loadActivityPicker();
    setupEventListeners();
});

// Load sport filter
async function loadSportFilter() {
    try {
        const sports = await API.getSports();
        const select = document.getElementById('compare-sport-filter');

        sports.forEach(sport => {
            const option = document.createElement('option');
            option.value = sport.sport;
            option.textContent = sport.sport.charAt(0).toUpperCase() + sport.sport.slice(1);
            select.appendChild(option);
        });

        select.addEventListener('change', filterActivityPicker);

    } catch (error) {
        console.error('Failed to load sports:', error);
    }
}

// Load activity picker
async function loadActivityPicker() {
    const container = document.getElementById('activity-picker');

    try {
        const data = await API.getActivities({ per_page: 100 });
        allActivities = data.activities;
        renderActivityPicker(allActivities);
    } catch (error) {
        console.error('Failed to load activities:', error);
        container.innerHTML = '<p class="error">Failed to load activities</p>';
    }
}

// Render activity picker items
function renderActivityPicker(activities) {
    const container = document.getElementById('activity-picker');

    if (activities.length === 0) {
        container.innerHTML = '<p class="no-data">No activities available</p>';
        return;
    }

    container.innerHTML = activities.map(activity => `
        <div class="picker-item ${selectedActivities.includes(activity.id) ? 'selected' : ''}"
             data-id="${activity.id}"
             onclick="toggleActivity(${activity.id})">
            <span class="item-sport">${activity.sport}</span>
            <div class="item-name">${activity.name}</div>
            <div class="item-date">${formatDate(activity.start_time)}</div>
            <div class="item-stats">
                <span>${formatDistance(activity.total_distance)}</span>
                <span>${formatDurationHuman(activity.total_timer_time)}</span>
            </div>
        </div>
    `).join('');
}

// Filter activity picker by sport
function filterActivityPicker() {
    const sport = document.getElementById('compare-sport-filter').value;

    if (!sport) {
        renderActivityPicker(allActivities);
    } else {
        const filtered = allActivities.filter(a => a.sport === sport);
        renderActivityPicker(filtered);
    }
}

// Toggle activity selection
function toggleActivity(id) {
    const index = selectedActivities.indexOf(id);

    if (index > -1) {
        selectedActivities.splice(index, 1);
    } else if (selectedActivities.length < 4) {
        selectedActivities.push(id);
    } else {
        showNotification('Maximum 4 activities can be compared', 'error');
        return;
    }

    updateSelectedDisplay();
    updatePickerDisplay();
}

// Update selected activities display
function updateSelectedDisplay() {
    const count = document.getElementById('selected-count');
    const list = document.getElementById('selected-list');
    const btn = document.getElementById('compare-btn');

    count.textContent = selectedActivities.length;
    btn.disabled = selectedActivities.length < 2;

    list.innerHTML = selectedActivities.map(id => {
        const activity = allActivities.find(a => a.id === id);
        return `
            <span class="selected-tag">
                ${activity ? activity.name.substring(0, 20) : id}
                <span class="remove" onclick="toggleActivity(${id})">&times;</span>
            </span>
        `;
    }).join('');
}

// Update picker display to show selected state
function updatePickerDisplay() {
    document.querySelectorAll('.picker-item').forEach(item => {
        const id = parseInt(item.dataset.id);
        item.classList.toggle('selected', selectedActivities.includes(id));
    });
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('compare-btn').addEventListener('click', runComparison);
}

// Run the comparison
async function runComparison() {
    if (selectedActivities.length < 2) return;

    const resultsSection = document.getElementById('comparison-results');
    resultsSection.style.display = 'block';

    try {
        const data = await API.compareActivities(selectedActivities);
        renderComparisonTable(data);
        renderComparisonCharts(data);
        renderComparisonMap(data);

        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Failed to compare activities:', error);
        showNotification('Failed to compare activities', 'error');
    }
}

// Render comparison table
function renderComparisonTable(data) {
    const header = document.getElementById('table-header');
    const tbody = document.querySelector('#comparison-table tbody');
    const activities = data.activities;

    // Update header
    header.innerHTML = '<th>Metric</th>' + activities.map(a => `<th>${a.name.substring(0, 25)}</th>`).join('');

    // Define metrics to compare
    const metrics = [
        { key: 'total_distance', label: 'Distance', format: v => formatDistance(v) },
        { key: 'total_timer_time', label: 'Duration', format: v => formatDuration(v) },
        { key: 'avg_speed', label: 'Avg Speed', format: v => formatSpeed(v) },
        { key: 'avg_heart_rate', label: 'Avg Heart Rate', format: v => v ? `${v} bpm` : '-' },
        { key: 'max_heart_rate', label: 'Max Heart Rate', format: v => v ? `${v} bpm` : '-' },
        { key: 'total_ascent', label: 'Elevation Gain', format: v => v ? `${Math.round(v)} m` : '-' },
        { key: 'total_calories', label: 'Calories', format: v => v ? formatNumber(v) : '-' },
        { key: 'avg_cadence', label: 'Avg Cadence', format: v => v || '-' }
    ];

    tbody.innerHTML = metrics.map(metric => {
        const values = activities.map(a => metric.format(a[metric.key]));
        return `
            <tr>
                <td>${metric.label}</td>
                ${values.map(v => `<td>${v}</td>`).join('')}
            </tr>
        `;
    }).join('');
}

// Render comparison charts
function renderComparisonCharts(data) {
    const activities = data.activities;
    const colors = getChartColors(activities.length);
    const labels = activities.map(a => a.name.substring(0, 15));

    // Distance comparison bar chart
    const distCtx = document.getElementById('compare-distance-chart').getContext('2d');
    new Chart(distCtx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Distance (km)',
                data: activities.map(a => (a.total_distance / 1000).toFixed(2)),
                backgroundColor: colors
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } }
        }
    });

    // Pace comparison bar chart
    const paceCtx = document.getElementById('compare-pace-chart').getContext('2d');
    new Chart(paceCtx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Avg Speed (km/h)',
                data: activities.map(a => a.avg_speed ? (a.avg_speed * 3.6).toFixed(1) : 0),
                backgroundColor: colors
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } }
        }
    });

    // Heart rate overlay line chart
    renderHROverlayChart(data, colors);

    // Elevation overlay chart
    renderElevationOverlayChart(data, colors);
}

// Render HR overlay chart
function renderHROverlayChart(data, colors) {
    const ctx = document.getElementById('compare-hr-chart').getContext('2d');
    const activities = data.activities;

    const datasets = activities.map((activity, index) => {
        const records = activity.records || [];
        const sampleRate = Math.ceil(records.length / 200);
        const sampledData = records.filter((_, i) => i % sampleRate === 0);

        return {
            label: activity.name.substring(0, 20),
            data: sampledData.map(r => r.heart_rate),
            borderColor: colors[index],
            backgroundColor: 'transparent',
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.1
        };
    });

    const maxLength = Math.max(...datasets.map(d => d.data.length));
    const labels = Array.from({ length: maxLength }, (_, i) => i);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { display: false },
                y: { title: { display: true, text: 'Heart Rate (bpm)' } }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

// Render elevation overlay chart
function renderElevationOverlayChart(data, colors) {
    const ctx = document.getElementById('compare-elevation-chart').getContext('2d');
    const activities = data.activities;

    const datasets = activities.map((activity, index) => {
        const records = activity.records || [];
        const sampleRate = Math.ceil(records.length / 200);
        const sampledData = records.filter((_, i) => i % sampleRate === 0);

        return {
            label: activity.name.substring(0, 20),
            data: sampledData.map(r => r.altitude),
            borderColor: colors[index],
            backgroundColor: colors[index] + '20',
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
            tension: 0.1
        };
    });

    const maxLength = Math.max(...datasets.map(d => d.data.length));
    const labels = Array.from({ length: maxLength }, (_, i) => i);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { display: false },
                y: { title: { display: true, text: 'Elevation (m)' } }
            }
        }
    });
}

// Render comparison map with multiple routes
function renderComparisonMap(data) {
    const activities = data.activities;
    const colors = getChartColors(activities.length);

    // Initialize map if not already
    if (compareMap) {
        compareMap.remove();
    }

    const mapContainer = document.getElementById('compare-map');
    compareMap = L.map(mapContainer);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(compareMap);

    const allBounds = [];
    const legend = document.getElementById('map-legend');
    legend.innerHTML = '';

    activities.forEach((activity, index) => {
        const gpsPoints = activity.gps_points || [];
        if (gpsPoints.length === 0) return;

        const coords = gpsPoints.map(p => [p.lat, p.lng]);
        const polyline = L.polyline(coords, {
            color: colors[index],
            weight: 3,
            opacity: 0.8
        }).addTo(compareMap);

        allBounds.push(...coords);

        // Add to legend
        legend.innerHTML += `
            <div class="legend-item">
                <div class="legend-color" style="background-color: ${colors[index]}"></div>
                <span>${activity.name.substring(0, 25)}</span>
            </div>
        `;
    });

    if (allBounds.length > 0) {
        compareMap.fitBounds(allBounds, { padding: [20, 20] });
    }
}

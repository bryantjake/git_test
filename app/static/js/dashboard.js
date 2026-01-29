/**
 * Dashboard page functionality
 */

document.addEventListener('DOMContentLoaded', async () => {
    await Promise.all([
        loadSummaryStats(),
        loadWeeklySummary(),
        loadRecentActivities(),
        loadMonthlyChart(),
        loadSportChart(),
        loadHeatmap()
    ]);
});

// Load all-time summary statistics
async function loadSummaryStats() {
    try {
        const stats = await API.getSummary();

        document.getElementById('total-activities').textContent = formatNumber(stats.total_activities);
        document.getElementById('total-distance').textContent = `${formatNumber(Math.round(stats.total_distance_km || 0))} km`;
        document.getElementById('total-time').textContent = formatDurationHuman(stats.total_duration);
        document.getElementById('total-elevation').textContent = `${formatNumber(Math.round(stats.total_elevation || 0))} m`;
    } catch (error) {
        console.error('Failed to load summary stats:', error);
    }
}

// Load weekly summary
async function loadWeeklySummary() {
    try {
        const stats = await API.getWeeklyStats();

        document.getElementById('week-activities').textContent = stats.total_activities || 0;
        document.getElementById('week-distance').textContent = formatDistance(stats.total_distance);
        document.getElementById('week-duration').textContent = formatDurationHuman(stats.total_duration);
        document.getElementById('week-calories').textContent = formatNumber(stats.total_calories || 0);
    } catch (error) {
        console.error('Failed to load weekly summary:', error);
    }
}

// Load recent activities
async function loadRecentActivities() {
    const container = document.getElementById('recent-activities');

    try {
        const data = await API.getActivities({ per_page: 5 });

        if (data.activities.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No activities yet. <a href="/upload">Upload your first activity</a></p>
                </div>
            `;
            return;
        }

        container.innerHTML = data.activities.map(createActivityItem).join('');
    } catch (error) {
        console.error('Failed to load activities:', error);
        container.innerHTML = '<p class="error">Failed to load activities</p>';
    }
}

// Load monthly distance chart
async function loadMonthlyChart() {
    try {
        const data = await API.getMonthlyTrend();
        const ctx = document.getElementById('monthly-chart').getContext('2d');

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.months.map(m => m.month_name.substring(0, 3)),
                datasets: [{
                    label: 'Distance (km)',
                    data: data.months.map(m => (m.total_distance / 1000).toFixed(1)),
                    backgroundColor: '#fc4c02',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: '#f0f0f0' }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Failed to load monthly chart:', error);
    }
}

// Load sport distribution chart
async function loadSportChart() {
    try {
        const sports = await API.getSports();

        if (sports.length === 0) return;

        const ctx = document.getElementById('sport-chart').getContext('2d');

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: sports.map(s => s.sport.charAt(0).toUpperCase() + s.sport.slice(1)),
                datasets: [{
                    data: sports.map(s => s.count),
                    backgroundColor: sports.map(s => getSportColor(s.sport)),
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { padding: 20 }
                    }
                },
                cutout: '60%'
            }
        });
    } catch (error) {
        console.error('Failed to load sport chart:', error);
    }
}

// Load activity heatmap
async function loadHeatmap() {
    const container = document.getElementById('heatmap-container');
    const yearLabel = document.getElementById('heatmap-year');
    const currentYear = new Date().getFullYear();

    yearLabel.textContent = currentYear;

    try {
        const data = await API.getHeatmap(currentYear);

        // Create heatmap grid
        const heatmapHtml = generateHeatmap(currentYear, data.data);
        container.innerHTML = heatmapHtml;
    } catch (error) {
        console.error('Failed to load heatmap:', error);
        container.innerHTML = '<p class="error">Failed to load heatmap</p>';
    }
}

// Generate heatmap HTML
function generateHeatmap(year, activityData) {
    const startDate = new Date(year, 0, 1);
    const endDate = new Date(year, 11, 31);

    // Adjust start to first Sunday
    const startDay = startDate.getDay();

    let html = '<div class="heatmap">';

    // Generate cells
    const current = new Date(startDate);
    current.setDate(current.getDate() - startDay); // Start from Sunday

    for (let week = 0; week < 53; week++) {
        for (let day = 0; day < 7; day++) {
            const dateKey = current.toISOString().split('T')[0];
            const dayData = activityData[dateKey];

            let level = 0;
            let title = dateKey;

            if (dayData) {
                if (dayData.count >= 3) level = 4;
                else if (dayData.count >= 2) level = 3;
                else if (dayData.distance >= 10000) level = 2;
                else level = 1;

                title = `${dateKey}: ${dayData.count} activities, ${formatDistance(dayData.distance)}`;
            }

            const isCurrentYear = current.getFullYear() === year;
            const cellClass = isCurrentYear ? `heatmap-day level-${level}` : 'heatmap-day outside';

            html += `<div class="${cellClass}" title="${title}" style="grid-column: ${week + 1}; grid-row: ${day + 1};"></div>`;

            current.setDate(current.getDate() + 1);
        }
    }

    html += '</div>';
    return html;
}

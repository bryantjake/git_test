/**
 * Statistics page functionality
 */

let currentPeriod = 'week';
let currentYear = new Date().getFullYear();
let currentMonth = new Date().getMonth() + 1;
let distanceTrendChart = null;
let durationTrendChart = null;
let yoyChart = null;
let distributionChart = null;

document.addEventListener('DOMContentLoaded', async () => {
    setupEventListeners();
    updateYearDisplay();
    updateMonthDisplay();
    await loadStats();
    await loadCharts();
    await loadCalendar();
});

// Setup event listeners
function setupEventListeners() {
    // Period buttons
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentPeriod = e.target.dataset.period;
            await loadStats();
        });
    });

    // Year navigation
    document.getElementById('prev-year').addEventListener('click', async () => {
        currentYear--;
        updateYearDisplay();
        await loadStats();
        await loadCharts();
    });

    document.getElementById('next-year').addEventListener('click', async () => {
        currentYear++;
        updateYearDisplay();
        await loadStats();
        await loadCharts();
    });

    // Month navigation
    document.getElementById('prev-month').addEventListener('click', async () => {
        currentMonth--;
        if (currentMonth < 1) {
            currentMonth = 12;
            currentYear--;
            updateYearDisplay();
        }
        updateMonthDisplay();
        await loadCalendar();
    });

    document.getElementById('next-month').addEventListener('click', async () => {
        currentMonth++;
        if (currentMonth > 12) {
            currentMonth = 1;
            currentYear++;
            updateYearDisplay();
        }
        updateMonthDisplay();
        await loadCalendar();
    });
}

// Update year display
function updateYearDisplay() {
    document.getElementById('selected-year').textContent = currentYear;
}

// Update month display
function updateMonthDisplay() {
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'];
    document.getElementById('selected-month').textContent = `${monthNames[currentMonth - 1]} ${currentYear}`;
}

// Load statistics based on current period
async function loadStats() {
    try {
        let stats;

        switch (currentPeriod) {
            case 'week':
                stats = await API.getWeeklyStats(currentYear);
                break;
            case 'month':
                stats = await API.getMonthlyStats(currentYear, currentMonth);
                break;
            case 'year':
                stats = await API.getAnnualStats(currentYear);
                break;
            case 'all':
                stats = await API.getSummary();
                break;
        }

        // Update summary stats
        document.getElementById('stat-activities').textContent = stats.total_activities || 0;
        document.getElementById('stat-distance').textContent = formatDistance(stats.total_distance);
        document.getElementById('stat-duration').textContent = formatDurationHuman(stats.total_duration);
        document.getElementById('stat-elevation').textContent = `${Math.round(stats.total_elevation || 0)} m`;
        document.getElementById('stat-calories').textContent = formatNumber(stats.total_calories || 0);

        // Update sport breakdown
        loadSportBreakdown(stats.by_sport || {});

    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Load sport breakdown cards
function loadSportBreakdown(bySport) {
    const container = document.getElementById('sport-breakdown');

    if (Object.keys(bySport).length === 0) {
        container.innerHTML = '<p class="no-data">No activity data for this period</p>';
        return;
    }

    container.innerHTML = Object.entries(bySport).map(([sport, data]) => `
        <div class="sport-stat-card ${sport}">
            <h4>${sport}</h4>
            <div class="stat-row">
                <span class="label">Activities</span>
                <span class="value">${data.count}</span>
            </div>
            <div class="stat-row">
                <span class="label">Distance</span>
                <span class="value">${formatDistance(data.distance)}</span>
            </div>
            <div class="stat-row">
                <span class="label">Duration</span>
                <span class="value">${formatDurationHuman(data.duration)}</span>
            </div>
            <div class="stat-row">
                <span class="label">Avg HR</span>
                <span class="value">${data.avg_heart_rate ? Math.round(data.avg_heart_rate) + ' bpm' : '-'}</span>
            </div>
        </div>
    `).join('');
}

// Load all charts
async function loadCharts() {
    await Promise.all([
        loadMonthlyTrendCharts(),
        loadYearOverYearChart(),
        loadDistributionChart()
    ]);
}

// Load monthly distance and duration trend charts
async function loadMonthlyTrendCharts() {
    try {
        const data = await API.getMonthlyTrend(currentYear);
        const labels = data.months.map(m => m.month_name.substring(0, 3));

        // Distance trend chart
        const distCtx = document.getElementById('distance-trend-chart').getContext('2d');
        if (distanceTrendChart) distanceTrendChart.destroy();

        distanceTrendChart = new Chart(distCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Distance (km)',
                    data: data.months.map(m => (m.total_distance / 1000).toFixed(1)),
                    borderColor: '#fc4c02',
                    backgroundColor: '#fc4c0240',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3
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

        // Duration trend chart
        const durCtx = document.getElementById('duration-trend-chart').getContext('2d');
        if (durationTrendChart) durationTrendChart.destroy();

        durationTrendChart = new Chart(durCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Duration (hours)',
                    data: data.months.map(m => (m.total_duration / 3600).toFixed(1)),
                    borderColor: '#0984e3',
                    backgroundColor: '#0984e340',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3
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
        console.error('Failed to load monthly trend charts:', error);
    }
}

// Load year-over-year comparison chart
async function loadYearOverYearChart() {
    try {
        const years = [currentYear - 2, currentYear - 1, currentYear];
        const data = await API.getYearlyComparison(years);

        const ctx = document.getElementById('yoy-chart').getContext('2d');
        if (yoyChart) yoyChart.destroy();

        yoyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.year),
                datasets: [
                    {
                        label: 'Distance (km)',
                        data: data.map(d => (d.total_distance / 1000).toFixed(0)),
                        backgroundColor: '#fc4c02'
                    },
                    {
                        label: 'Activities',
                        data: data.map(d => d.total_activities),
                        backgroundColor: '#0984e3'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
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
        console.error('Failed to load YoY chart:', error);
    }
}

// Load activity distribution chart
async function loadDistributionChart() {
    try {
        const stats = await API.getAnnualStats(currentYear);
        const bySport = stats.by_sport || {};

        if (Object.keys(bySport).length === 0) return;

        const ctx = document.getElementById('distribution-chart').getContext('2d');
        if (distributionChart) distributionChart.destroy();

        const sports = Object.keys(bySport);
        const distances = sports.map(s => (bySport[s].distance / 1000).toFixed(1));

        distributionChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: sports.map(s => s.charAt(0).toUpperCase() + s.slice(1)),
                datasets: [{
                    data: distances,
                    backgroundColor: sports.map(s => getSportColor(s)),
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.label}: ${context.raw} km`;
                            }
                        }
                    }
                },
                cutout: '50%'
            }
        });

    } catch (error) {
        console.error('Failed to load distribution chart:', error);
    }
}

// Load activity calendar
async function loadCalendar() {
    const container = document.getElementById('activity-calendar');

    try {
        const heatmapData = await API.getHeatmap(currentYear);
        const activityData = heatmapData.data;

        // Generate calendar
        const daysInMonth = new Date(currentYear, currentMonth, 0).getDate();
        const firstDay = new Date(currentYear, currentMonth - 1, 1).getDay();

        let html = '';

        // Day headers
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        dayNames.forEach(day => {
            html += `<div class="calendar-header">${day}</div>`;
        });

        // Empty cells for days before start of month
        for (let i = 0; i < firstDay; i++) {
            html += '<div class="calendar-day empty"></div>';
        }

        // Day cells
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const hasActivity = activityData[dateStr];
            const activityClass = hasActivity ? 'has-activity' : '';
            const title = hasActivity
                ? `${dateStr}: ${hasActivity.count} activities, ${formatDistance(hasActivity.distance)}`
                : dateStr;

            html += `<div class="calendar-day ${activityClass}" title="${title}">${day}</div>`;
        }

        container.innerHTML = html;

    } catch (error) {
        console.error('Failed to load calendar:', error);
        container.innerHTML = '<p class="error">Failed to load calendar</p>';
    }
}

/**
 * Personal Records page functionality
 */

let currentSport = '';

document.addEventListener('DOMContentLoaded', async () => {
    await loadSportTabs();
    await loadRecords();
});

// Load sport tabs
async function loadSportTabs() {
    try {
        const sports = await API.getSports();
        const container = document.getElementById('sport-tabs');

        // Add sport-specific tabs
        sports.forEach(sport => {
            const btn = document.createElement('button');
            btn.className = 'sport-tab';
            btn.dataset.sport = sport.sport;
            btn.textContent = sport.sport.charAt(0).toUpperCase() + sport.sport.slice(1);
            btn.addEventListener('click', () => selectSport(sport.sport));
            container.appendChild(btn);
        });

        // Setup "All Sports" button
        container.querySelector('[data-sport=""]').addEventListener('click', () => selectSport(''));

    } catch (error) {
        console.error('Failed to load sports:', error);
    }
}

// Select a sport filter
async function selectSport(sport) {
    currentSport = sport;

    // Update active tab
    document.querySelectorAll('.sport-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.sport === sport);
    });

    await loadRecords();
}

// Load personal records
async function loadRecords() {
    const container = document.getElementById('records-container');
    container.innerHTML = '<div class="loading">Loading records...</div>';

    try {
        const records = await API.getRecords(currentSport);

        if (Object.keys(records).length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No personal records yet. Upload more activities to set records!</p>
                </div>
            `;
            return;
        }

        let html = '';

        // Group records by sport
        Object.entries(records).forEach(([sport, types]) => {
            html += `
                <div class="sport-records">
                    <h3>${sport}</h3>
            `;

            // Group by record type
            Object.entries(types).forEach(([type, recordList]) => {
                html += `
                    <div class="record-category">
                        <h4>${formatRecordType(type)}</h4>
                `;

                recordList.forEach(record => {
                    html += `
                        <div class="record-item">
                            <div>
                                <span class="record-name">${record.record_name}</span>
                                <span class="record-date">${formatDate(record.achieved_at)}</span>
                            </div>
                            <span class="record-value">${record.formatted_value}</span>
                        </div>
                    `;
                });

                html += '</div>';
            });

            html += '</div>';
        });

        container.innerHTML = html;

    } catch (error) {
        console.error('Failed to load records:', error);
        container.innerHTML = '<p class="error">Failed to load records</p>';
    }
}

// Format record type for display
function formatRecordType(type) {
    const typeNames = {
        'distance': 'Best Times',
        'max_heart_rate': 'Heart Rate',
        'max_speed': 'Speed',
        'max_power': 'Power',
        'longest': 'Longest Efforts'
    };
    return typeNames[type] || type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

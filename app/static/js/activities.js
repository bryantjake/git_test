/**
 * Activities list page functionality
 */

let currentPage = 1;
let currentFilters = {};

document.addEventListener('DOMContentLoaded', async () => {
    await loadSportFilter();
    await loadYearFilter();
    setupFilterListeners();
    await loadActivities();
});

// Load sport filter options
async function loadSportFilter() {
    try {
        const sports = await API.getSports();
        const select = document.getElementById('sport-filter');

        sports.forEach(sport => {
            const option = document.createElement('option');
            option.value = sport.sport;
            option.textContent = sport.sport.charAt(0).toUpperCase() + sport.sport.slice(1) + ` (${sport.count})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load sports:', error);
    }
}

// Load year filter options
async function loadYearFilter() {
    try {
        const data = await API.getActivities({ per_page: 1 });
        const select = document.getElementById('year-filter');

        // Get current year and go back 5 years
        const currentYear = new Date().getFullYear();
        for (let year = currentYear; year >= currentYear - 5; year--) {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            select.appendChild(option);
        }
    } catch (error) {
        console.error('Failed to set up year filter:', error);
    }
}

// Setup filter event listeners
function setupFilterListeners() {
    document.getElementById('sport-filter').addEventListener('change', applyFilters);
    document.getElementById('year-filter').addEventListener('change', applyFilters);
    document.getElementById('month-filter').addEventListener('change', applyFilters);
    document.getElementById('clear-filters').addEventListener('click', clearFilters);
}

// Apply filters and reload activities
async function applyFilters() {
    currentPage = 1;
    currentFilters = {
        sport: document.getElementById('sport-filter').value,
        year: document.getElementById('year-filter').value,
        month: document.getElementById('month-filter').value
    };

    // Remove empty filters
    Object.keys(currentFilters).forEach(key => {
        if (!currentFilters[key]) delete currentFilters[key];
    });

    await loadActivities();
}

// Clear all filters
async function clearFilters() {
    document.getElementById('sport-filter').value = '';
    document.getElementById('year-filter').value = '';
    document.getElementById('month-filter').value = '';
    currentFilters = {};
    currentPage = 1;
    await loadActivities();
}

// Load activities with current filters
async function loadActivities() {
    const container = document.getElementById('activities-list');
    container.innerHTML = '<div class="loading">Loading activities...</div>';

    try {
        const params = {
            page: currentPage,
            per_page: 20,
            ...currentFilters
        };

        const data = await API.getActivities(params);

        if (data.activities.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No activities found. ${Object.keys(currentFilters).length > 0 ? 'Try adjusting your filters.' : '<a href="/upload">Upload your first activity</a>'}</p>
                </div>
            `;
            document.getElementById('pagination').innerHTML = '';
            return;
        }

        container.innerHTML = data.activities.map(createActivityItem).join('');
        renderPagination(data);
    } catch (error) {
        console.error('Failed to load activities:', error);
        container.innerHTML = '<p class="error">Failed to load activities</p>';
    }
}

// Render pagination controls
function renderPagination(data) {
    const container = document.getElementById('pagination');

    if (data.pages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '';

    // Previous button
    html += `<button ${currentPage === 1 ? 'disabled' : ''} onclick="goToPage(${currentPage - 1})">Prev</button>`;

    // Page numbers
    for (let i = 1; i <= data.pages; i++) {
        if (i === 1 || i === data.pages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            html += `<button class="${i === currentPage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            html += '<span>...</span>';
        }
    }

    // Next button
    html += `<button ${currentPage === data.pages ? 'disabled' : ''} onclick="goToPage(${currentPage + 1})">Next</button>`;

    container.innerHTML = html;
}

// Go to specific page
async function goToPage(page) {
    currentPage = page;
    await loadActivities();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

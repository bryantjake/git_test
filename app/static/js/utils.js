/**
 * Utility functions for the Garmin Activity Tracker
 */

// Format duration from seconds to HH:MM:SS
function formatDuration(seconds) {
    if (!seconds) return '-';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hrs > 0) {
        return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Format duration to human readable
function formatDurationHuman(seconds) {
    if (!seconds) return '-';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);

    if (hrs > 0) {
        return `${hrs}h ${mins}m`;
    }
    return `${mins}m`;
}

// Format distance in meters to km
function formatDistance(meters) {
    if (!meters) return '-';
    const km = meters / 1000;
    return `${km.toFixed(2)} km`;
}

// Format distance to just the number
function formatDistanceValue(meters) {
    if (!meters) return '0';
    return (meters / 1000).toFixed(2);
}

// Format speed (m/s) to pace (min/km)
function formatPace(speedMs) {
    if (!speedMs || speedMs === 0) return '-';
    const paceSeconds = 1000 / speedMs;
    const mins = Math.floor(paceSeconds / 60);
    const secs = Math.floor(paceSeconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')} /km`;
}

// Format speed (m/s) to km/h
function formatSpeed(speedMs) {
    if (!speedMs) return '-';
    const kmh = speedMs * 3.6;
    return `${kmh.toFixed(1)} km/h`;
}

// Format date to readable string
function formatDate(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

// Format date and time
function formatDateTime(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
    });
}

// Format number with commas
function formatNumber(num) {
    if (!num) return '0';
    return num.toLocaleString();
}

// Get sport color
function getSportColor(sport) {
    const colors = {
        running: '#fc4c02',
        cycling: '#0984e3',
        swimming: '#00cec9',
        hiking: '#6c5ce7',
        gym: '#e17055',
        walking: '#a29bfe',
        training: '#fdcb6e'
    };
    return colors[sport] || '#636e72';
}

// Get chart colors for multiple datasets
function getChartColors(count) {
    const baseColors = [
        '#fc4c02',
        '#0984e3',
        '#00cec9',
        '#6c5ce7',
        '#e17055',
        '#00b894',
        '#fdcb6e',
        '#d63031'
    ];
    return baseColors.slice(0, count);
}

// Create activity item HTML
function createActivityItem(activity) {
    const distance = formatDistance(activity.total_distance);
    const duration = formatDurationHuman(activity.total_timer_time);
    const pace = activity.sport === 'cycling'
        ? formatSpeed(activity.avg_speed)
        : formatPace(activity.avg_speed);

    return `
        <div class="activity-item" onclick="window.location.href='/activity/${activity.id}'">
            <span class="sport-badge ${activity.sport}">${activity.sport}</span>
            <div class="activity-info">
                <h4>${activity.name}</h4>
                <span class="date">${formatDate(activity.start_time)}</span>
            </div>
            <div class="activity-metrics">
                <div class="metric">
                    <span class="value">${distance}</span>
                    <span class="label">Distance</span>
                </div>
                <div class="metric">
                    <span class="value">${duration}</span>
                    <span class="label">Time</span>
                </div>
                <div class="metric">
                    <span class="value">${pace}</span>
                    <span class="label">${activity.sport === 'cycling' ? 'Speed' : 'Pace'}</span>
                </div>
            </div>
        </div>
    `;
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        color: white;
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;

    if (type === 'success') {
        notification.style.backgroundColor = '#00b894';
    } else if (type === 'error') {
        notification.style.backgroundColor = '#d63031';
    } else {
        notification.style.backgroundColor = '#0984e3';
    }

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add animation keyframes
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

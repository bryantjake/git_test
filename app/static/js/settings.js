/**
 * Settings page functionality for Garmin Connect sync
 */

document.addEventListener('DOMContentLoaded', async () => {
    await loadGarminStatus();
    setupEventListeners();
});

// Load current Garmin connection status
async function loadGarminStatus() {
    try {
        const response = await fetch('/api/garmin/status');
        const data = await response.json();

        updateConnectionUI(data.settings);

        if (data.settings.is_connected) {
            // Try to restore session
            await restoreSession();
            await loadSyncLogs();
        }
    } catch (error) {
        console.error('Failed to load Garmin status:', error);
    }
}

// Update UI based on connection status
function updateConnectionUI(settings) {
    const statusIndicator = document.getElementById('status-indicator');
    const userInfo = document.getElementById('user-info');
    const loginForm = document.getElementById('login-form');
    const connectedActions = document.getElementById('connected-actions');
    const autoSyncSection = document.getElementById('auto-sync-section');
    const syncHistorySection = document.getElementById('sync-history-section');
    const previewSection = document.getElementById('activities-preview-section');

    if (settings.is_connected) {
        // Show connected state
        statusIndicator.className = 'status-indicator connected';
        statusIndicator.querySelector('.status-text').textContent = 'Connected';

        if (settings.garmin_display_name || settings.garmin_email) {
            userInfo.style.display = 'block';
            document.getElementById('user-name').textContent = settings.garmin_display_name || '';
            document.getElementById('user-email').textContent = settings.garmin_email || '';
        }

        loginForm.style.display = 'none';
        connectedActions.style.display = 'flex';
        autoSyncSection.style.display = 'block';
        syncHistorySection.style.display = 'block';
        previewSection.style.display = 'block';

        // Update settings controls
        document.getElementById('auto-sync-toggle').checked = settings.auto_sync_enabled;
        document.getElementById('sync-interval').value = settings.sync_interval_minutes;
        document.getElementById('sync-days').value = settings.sync_days_back;

        // Update last sync info
        if (settings.last_sync_at) {
            document.getElementById('last-sync-time').textContent = formatDateTime(settings.last_sync_at);
            document.getElementById('last-sync-status').textContent = settings.last_sync_status || '-';
            document.getElementById('last-sync-status').className = settings.last_sync_status === 'success' ? 'success' : 'error';
            document.getElementById('last-sync-count').textContent = settings.last_sync_count || 0;
        }

    } else {
        // Show disconnected state
        statusIndicator.className = 'status-indicator disconnected';
        statusIndicator.querySelector('.status-text').textContent = 'Not Connected';
        userInfo.style.display = 'none';

        loginForm.style.display = 'block';
        connectedActions.style.display = 'none';
        autoSyncSection.style.display = 'none';
        syncHistorySection.style.display = 'none';
        previewSection.style.display = 'none';
    }
}

// Restore session from stored tokens
async function restoreSession() {
    try {
        const response = await fetch('/api/garmin/restore-session', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            console.log('Session restored successfully');
            await loadGarminActivities();
        }
    } catch (error) {
        console.error('Failed to restore session:', error);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Connect button
    document.getElementById('connect-btn').addEventListener('click', connectToGarmin);

    // Disconnect button
    document.getElementById('disconnect-btn').addEventListener('click', disconnectFromGarmin);

    // Sync now button
    document.getElementById('sync-now-btn').addEventListener('click', syncNow);

    // Save settings button
    document.getElementById('save-settings-btn').addEventListener('click', saveSettings);

    // Refresh preview button
    document.getElementById('refresh-preview-btn').addEventListener('click', loadGarminActivities);

    // Enter key on password field
    document.getElementById('garmin-password').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') connectToGarmin();
    });
}

// Connect to Garmin
async function connectToGarmin() {
    const email = document.getElementById('garmin-email').value.trim();
    const password = document.getElementById('garmin-password').value;

    if (!email || !password) {
        showNotification('Please enter your email and password', 'error');
        return;
    }

    const btn = document.getElementById('connect-btn');
    btn.disabled = true;
    btn.textContent = 'Connecting...';

    try {
        const response = await fetch('/api/garmin/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Successfully connected to Garmin!', 'success');
            updateConnectionUI(data.settings);
            await loadGarminActivities();
            await loadSyncLogs();

            // Clear password field
            document.getElementById('garmin-password').value = '';
        } else {
            showNotification(data.error || 'Failed to connect', 'error');
        }
    } catch (error) {
        showNotification('Connection failed: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Connect to Garmin';
    }
}

// Disconnect from Garmin
async function disconnectFromGarmin() {
    if (!confirm('Are you sure you want to disconnect from Garmin Connect?')) {
        return;
    }

    try {
        const response = await fetch('/api/garmin/disconnect', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            showNotification('Disconnected from Garmin', 'success');
            await loadGarminStatus();
        }
    } catch (error) {
        showNotification('Failed to disconnect: ' + error.message, 'error');
    }
}

// Sync activities now
async function syncNow() {
    const btn = document.getElementById('sync-now-btn');
    const progress = document.getElementById('sync-progress');
    const progressText = document.getElementById('sync-progress-text');

    btn.disabled = true;
    progress.style.display = 'block';
    progressText.textContent = 'Syncing activities from Garmin...';

    try {
        const response = await fetch('/api/garmin/sync', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            const results = data.results;
            progressText.textContent = `Synced ${results.synced} activities, ${results.skipped} skipped`;

            if (results.synced > 0) {
                showNotification(`Successfully synced ${results.synced} activities!`, 'success');
            } else {
                showNotification('No new activities to sync', 'info');
            }

            // Show new records if any
            if (results.new_records && results.new_records.length > 0) {
                const recordNames = results.new_records.map(r => r.record_name).join(', ');
                showNotification(`New personal records: ${recordNames}`, 'success');
            }

            await loadGarminStatus();
            await loadSyncLogs();
        } else {
            progressText.textContent = 'Sync failed';
            showNotification(data.error || 'Sync failed', 'error');
        }
    } catch (error) {
        progressText.textContent = 'Sync failed';
        showNotification('Sync failed: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        setTimeout(() => {
            progress.style.display = 'none';
        }, 3000);
    }
}

// Save auto-sync settings
async function saveSettings() {
    const settings = {
        auto_sync_enabled: document.getElementById('auto-sync-toggle').checked,
        sync_interval_minutes: parseInt(document.getElementById('sync-interval').value),
        sync_days_back: parseInt(document.getElementById('sync-days').value)
    };

    try {
        const response = await fetch('/api/garmin/settings', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        const data = await response.json();
        showNotification('Settings saved!', 'success');
    } catch (error) {
        showNotification('Failed to save settings: ' + error.message, 'error');
    }
}

// Load recent sync logs
async function loadSyncLogs() {
    try {
        const response = await fetch('/api/garmin/sync-logs?limit=5');
        const logs = await response.json();

        const container = document.getElementById('sync-logs');

        if (logs.length === 0) {
            container.innerHTML = '<p class="no-data">No sync history yet</p>';
            return;
        }

        container.innerHTML = logs.map(log => `
            <div class="sync-log-item ${log.status}">
                <div class="log-time">${formatDateTime(log.started_at)}</div>
                <div class="log-status ${log.status}">${log.status}</div>
                <div class="log-counts">
                    <span class="synced">${log.activities_synced} synced</span>
                    <span class="skipped">${log.activities_skipped} skipped</span>
                    ${log.activities_failed > 0 ? `<span class="failed">${log.activities_failed} failed</span>` : ''}
                </div>
                ${log.error_message ? `<div class="log-error">${log.error_message}</div>` : ''}
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load sync logs:', error);
    }
}

// Load Garmin activities preview
async function loadGarminActivities() {
    const container = document.getElementById('garmin-activities-list');
    container.innerHTML = '<div class="loading">Loading activities from Garmin...</div>';

    try {
        const response = await fetch('/api/garmin/activities?limit=10');

        if (!response.ok) {
            const data = await response.json();
            container.innerHTML = `<p class="error">${data.error || 'Failed to load activities'}</p>`;
            return;
        }

        const activities = await response.json();

        if (activities.length === 0) {
            container.innerHTML = '<p class="no-data">No recent activities found</p>';
            return;
        }

        container.innerHTML = activities.map(a => `
            <div class="garmin-activity-item">
                <div class="activity-sport">${a.sport}</div>
                <div class="activity-name">${a.name || 'Untitled'}</div>
                <div class="activity-date">${formatDateTime(a.start_time)}</div>
                <div class="activity-stats">
                    ${a.distance ? `<span>${formatDistance(a.distance)}</span>` : ''}
                    ${a.duration ? `<span>${formatDurationHuman(a.duration)}</span>` : ''}
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = `<p class="error">Failed to load activities: ${error.message}</p>`;
    }
}

// Utility function to format datetime
function formatDateTime(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
    });
}

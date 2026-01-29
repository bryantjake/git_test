/**
 * API client for the Garmin Activity Tracker
 */

const API = {
    baseUrl: '/api',

    // Generic fetch wrapper
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Request failed');
        }

        return response.json();
    },

    // Activities
    async getActivities(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return this.request(`/activities${queryString ? '?' + queryString : ''}`);
    },

    async getActivity(id, includeDetails = true) {
        return this.request(`/activities/${id}?details=${includeDetails}`);
    },

    async deleteActivity(id) {
        return this.request(`/activities/${id}`, { method: 'DELETE' });
    },

    async updateActivity(id, data) {
        return this.request(`/activities/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    },

    // Upload
    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${this.baseUrl}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Upload failed');
        }

        return response.json();
    },

    async uploadBatch(files) {
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));

        const response = await fetch(`${this.baseUrl}/upload/batch`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Batch upload failed');
        }

        return response.json();
    },

    // Statistics
    async getSummary() {
        return this.request('/stats/summary');
    },

    async getWeeklyStats(year, week) {
        const params = new URLSearchParams();
        if (year) params.append('year', year);
        if (week) params.append('week', week);
        return this.request(`/stats/weekly?${params}`);
    },

    async getMonthlyStats(year, month) {
        const params = new URLSearchParams();
        if (year) params.append('year', year);
        if (month) params.append('month', month);
        return this.request(`/stats/monthly?${params}`);
    },

    async getAnnualStats(year) {
        const params = year ? `?year=${year}` : '';
        return this.request(`/stats/annual${params}`);
    },

    async getYearlyComparison(years) {
        const params = years ? `?years=${years.join(',')}` : '';
        return this.request(`/stats/yearly-comparison${params}`);
    },

    async getMonthlyTrend(year) {
        const params = year ? `?year=${year}` : '';
        return this.request(`/stats/monthly-trend${params}`);
    },

    async getHeatmap(year) {
        const params = year ? `?year=${year}` : '';
        return this.request(`/stats/heatmap${params}`);
    },

    // Personal Records
    async getRecords(sport) {
        const params = sport ? `?sport=${sport}` : '';
        return this.request(`/records${params}`);
    },

    async getActivityRecords(activityId) {
        return this.request(`/records/activity/${activityId}`);
    },

    // Comparison
    async compareActivities(ids) {
        return this.request(`/compare?ids=${ids.join(',')}`);
    },

    // Sports
    async getSports() {
        return this.request('/sports');
    }
};

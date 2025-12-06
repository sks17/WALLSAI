/**
 * WALLS API Client Module
 * 
 * Provides a clean interface to all backend AI endpoints.
 * Handles request/response formatting, error handling, and caching.
 */

const WallsAPI = (function() {
    'use strict';

    // ========================================================================
    // Configuration
    // ========================================================================
    
    const BASE_URL = '/api/v2';
    const LEGACY_URL = '/api';
    
    const DEFAULT_HEADERS = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    };

    // Request cache for short-term deduplication
    const requestCache = new Map();
    const CACHE_TTL = 5000; // 5 seconds

    // ========================================================================
    // Utility Functions
    // ========================================================================

    /**
     * Generate a cache key for a request
     */
    function getCacheKey(url, options) {
        return `${options?.method || 'GET'}:${url}:${JSON.stringify(options?.body || '')}`;
    }

    /**
     * Check if cached response is still valid
     */
    function getCachedResponse(key) {
        const cached = requestCache.get(key);
        if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
            return cached.data;
        }
        requestCache.delete(key);
        return null;
    }

    /**
     * Cache a response
     */
    function cacheResponse(key, data) {
        requestCache.set(key, { data, timestamp: Date.now() });
    }

    /**
     * Make an API request with error handling
     */
    async function request(endpoint, options = {}) {
        const url = endpoint.startsWith('/') ? endpoint : `${BASE_URL}/${endpoint}`;
        
        const config = {
            ...options,
            headers: {
                ...DEFAULT_HEADERS,
                ...options.headers
            }
        };

        // Check cache for GET requests
        if (!options.method || options.method === 'GET') {
            const cacheKey = getCacheKey(url, config);
            const cached = getCachedResponse(cacheKey);
            if (cached) {
                console.debug('[API] Cache hit:', url);
                return cached;
            }
        }

        try {
            console.debug('[API] Request:', options.method || 'GET', url);
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new APIError(
                    errorData.error || `HTTP ${response.status}`,
                    response.status,
                    errorData
                );
            }

            const data = await response.json();
            
            // Cache GET responses
            if (!options.method || options.method === 'GET') {
                const cacheKey = getCacheKey(url, config);
                cacheResponse(cacheKey, data);
            }

            return data;
        } catch (error) {
            if (error instanceof APIError) {
                throw error;
            }
            throw new APIError(`Network error: ${error.message}`, 0, null);
        }
    }

    /**
     * Custom API Error class
     */
    class APIError extends Error {
        constructor(message, status, data) {
            super(message);
            this.name = 'APIError';
            this.status = status;
            this.data = data;
        }
    }

    // ========================================================================
    // Prediction API
    // ========================================================================

    /**
     * Run ML inference on user input
     * 
     * @param {Object} userFeatures - Survey responses and user data
     * @param {string} freeText - Optional free-form text input
     * @param {string} userId - Optional user identifier
     * @param {boolean} saveResult - Whether to save to history (default: true)
     * @returns {Promise<Object>} Prediction results with scores and classifications
     */
    async function predict(userFeatures, freeText = '', userId = 'anonymous', saveResult = true) {
        // Use Firebase UID if available
        const effectiveUserId = window.USER_UID || userId;
        
        const response = await request(`${BASE_URL}/predict`, {
            method: 'POST',
            body: JSON.stringify({
                answers: userFeatures,
                free_text: freeText,
                user_id: effectiveUserId,
                save: saveResult
            })
        });

        // Save to Firestore via user API (in addition to backend save)
        if (saveResult && window.USER_UID) {
            try {
                await saveSurveyToFirestore(window.USER_UID, {
                    timestamp: new Date().toISOString(),
                    scores: response.scores,
                    text: freeText,
                    raw_responses: userFeatures,
                    prediction: response.prediction,
                    confidence: response.confidence,
                    probabilities: response.probabilities,
                    classifications: response.classifications,
                    intensity_values: response.intensity_values
                });
                console.log('[API] Survey saved to Firestore');
            } catch (e) {
                console.warn('[API] Firestore save failed:', e);
            }
        }

        // Emit event for visualization updates
        window.dispatchEvent(new CustomEvent('walls:prediction', {
            detail: response
        }));

        return response;
    }
    
    /**
     * Save survey entry to Firestore
     */
    async function saveSurveyToFirestore(uid, entry) {
        return fetch('/api/user/save-survey', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ uid, entry })
        }).then(r => r.json());
    }

    /**
     * Get prediction using legacy API (for backwards compatibility)
     */
    async function predictLegacy(answers) {
        return request(`${LEGACY_URL}/predict`, {
            method: 'POST',
            body: JSON.stringify({ answers })
        });
    }

    // ========================================================================
    // History API
    // ========================================================================

    /**
     * Get evaluation history
     * 
     * @param {string} userId - Optional user filter
     * @param {number} limit - Max records (default: 50)
     * @returns {Promise<Object>} History data with evaluations array
     */
    async function getHistory(userId = null, limit = 50) {
        // Use Firebase UID if available
        const effectiveUserId = window.USER_UID || userId;
        
        // Try Firestore endpoint first if user is authenticated
        if (window.USER_UID) {
            try {
                const firestoreHistory = await getFirestoreHistory(window.USER_UID, limit);
                if (firestoreHistory && firestoreHistory.history) {
                    console.log('[API] Loaded history from Firestore:', firestoreHistory.history.length);
                    return firestoreHistory;
                }
            } catch (e) {
                console.warn('[API] Firestore history failed, falling back:', e);
            }
        }
        
        // Fallback to legacy endpoint
        const params = new URLSearchParams();
        if (effectiveUserId) params.append('user_id', effectiveUserId);
        params.append('limit', limit.toString());
        
        return request(`${BASE_URL}/history?${params}`);
    }
    
    /**
     * Get history from Firestore via user API
     */
    async function getFirestoreHistory(uid, limit = 50) {
        const response = await fetch(`/api/user/history/${uid}?limit=${limit}`, {
            credentials: 'include'
        });
        return response.json();
    }

    /**
     * Get computed metrics and trends
     * 
     * @param {string} userId - Optional user filter
     * @returns {Promise<Object>} Metrics with trends, flags, averages
     */
    async function getMetrics(userId = null) {
        const params = new URLSearchParams();
        if (userId) params.append('user_id', userId);
        
        return request(`${BASE_URL}/metrics?${params}`);
    }

    /**
     * Get clinical thresholds for score interpretation
     */
    async function getThresholds() {
        return request(`${BASE_URL}/thresholds`);
    }

    // ========================================================================
    // Status API
    // ========================================================================

    /**
     * Check API and model status
     */
    async function getStatus() {
        return request(`${BASE_URL}/status`);
    }

    /**
     * Ping the server (health check)
     */
    async function ping() {
        return request(`${LEGACY_URL}/ping`);
    }

    // ========================================================================
    // User ID & Account-Based Persistence
    // ========================================================================
    
    // Note: Local storage has been removed in favor of account-based Firestore persistence.
    // New users start with empty history (all values at 0).

    /**
     * Get the current user ID (Firebase UID)
     * 
     * Account-based persistence: Uses Firebase UID when available.
     * New users automatically start with empty/zero values.
     */
    function getUserId() {
        // Prefer Firebase UID for account-based persistence
        if (window.USER_UID) {
            return window.USER_UID;
        }
        
        // Fallback to session user ID (set by Flask template)
        if (window.SESSION_USER_ID && window.SESSION_USER_ID !== 'None') {
            return window.SESSION_USER_ID;
        }
        
        // Anonymous user (data will not persist across sessions)
        return 'anonymous';
    }

    /**
     * @deprecated Local storage removed - entries saved to Firestore
     */
    function saveLocalEntry(entry) {
        // Entries are saved to Firestore via saveSurveyToFirestore()
        console.debug('[API] saveLocalEntry deprecated - using Firestore');
        return entry;
    }

    /**
     * @deprecated Use getHistory() which fetches from Firestore
     */
    function getLocalHistory() {
        console.debug('[API] getLocalHistory deprecated - use getHistory()');
        return [];
    }

    /**
     * @deprecated Local storage no longer used
     */
    function clearLocalHistory() {
        console.debug('[API] clearLocalHistory deprecated');
    }

    // ========================================================================
    // Data Processing Utilities
    // ========================================================================

    /**
     * Compute time series data for charts
     * 
     * @param {Array} history - Array of evaluation records
     * @param {string} metric - Metric to extract (e.g., 'stress_score')
     * @returns {Object} { labels: [], values: [] }
     */
    function computeTimeSeries(history, metric) {
        const sorted = [...history].sort((a, b) => 
            new Date(a.timestamp) - new Date(b.timestamp)
        );

        return {
            labels: sorted.map(r => {
                const d = new Date(r.timestamp);
                return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            }),
            values: sorted.map(r => r.scores?.[metric] ?? null)
        };
    }

    /**
     * Compute moving average
     * 
     * @param {Array} values - Numeric array
     * @param {number} window - Window size
     * @returns {Array} Moving averages
     */
    function computeMovingAverage(values, window = 3) {
        const result = [];
        for (let i = 0; i < values.length; i++) {
            const start = Math.max(0, i - window + 1);
            const subset = values.slice(start, i + 1).filter(v => v !== null);
            result.push(subset.length > 0 ? subset.reduce((a, b) => a + b, 0) / subset.length : null);
        }
        return result;
    }

    /**
     * Detect anomalies in time series
     * 
     * @param {Array} values - Numeric array
     * @param {number} threshold - Standard deviations for anomaly
     * @returns {Array} Indices of anomalous values
     */
    function detectAnomalies(values, threshold = 2) {
        const filtered = values.filter(v => v !== null);
        if (filtered.length < 3) return [];

        const mean = filtered.reduce((a, b) => a + b, 0) / filtered.length;
        const std = Math.sqrt(
            filtered.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / filtered.length
        );

        if (std === 0) return [];

        return values
            .map((v, i) => ({ v, i }))
            .filter(({ v }) => v !== null && Math.abs(v - mean) > threshold * std)
            .map(({ i }) => i);
    }

    /**
     * Format RL-ready entry structure
     */
    function formatRLEntry(features, freeText, mlOutputs) {
        return {
            timestamp: new Date().toISOString(),
            features: features,
            free_text: freeText || '',
            ml_outputs: mlOutputs,
            policy: {
                state: JSON.stringify({
                    scores: mlOutputs.scores,
                    input_count: Object.keys(features).length
                }),
                reward: null,
                next_question: null
            }
        };
    }

    // ========================================================================
    // Event Subscription
    // ========================================================================

    const subscribers = new Map();

    /**
     * Subscribe to prediction events
     */
    function onPrediction(callback) {
        const handler = (e) => callback(e.detail);
        window.addEventListener('walls:prediction', handler);
        return () => window.removeEventListener('walls:prediction', handler);
    }

    // ========================================================================
    // Public API
    // ========================================================================

    return {
        // Prediction
        predict,
        predictLegacy,
        
        // History & Metrics
        getHistory,
        getMetrics,
        getThresholds,
        
        // Status
        getStatus,
        ping,
        
        // Local storage
        getUserId,
        saveLocalEntry,
        getLocalHistory,
        clearLocalHistory,
        
        // Data processing
        computeTimeSeries,
        computeMovingAverage,
        detectAnomalies,
        formatRLEntry,
        
        // Events
        onPrediction,
        
        // Error class
        APIError
    };
})();

// Make available globally
window.WallsAPI = WallsAPI;


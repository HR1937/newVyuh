// Diagnostic: confirm script file execution
try { console.info('[UI] dashboard.js loaded'); } catch(_) {}

class VyuhMitraDashboard {
    constructor() {
        this.apiBaseUrl = 'http://127.0.0.1:5000';
        this.refreshInterval = 60000; // 1 minute
        this.isRefreshing = false;
        this.charts = {};
        this.retryCount = 0;
        this.maxRetries = 3;
        this.simulationRunning = false;
        
        console.log('🚂 VyuhMitra Dashboard Starting...');
        this.init();
    }
    
    
    async init() {
        try {
            console.log('📱 Initializing VyuhMitra Dashboard...');
            this.setupHeightManagement();
            
            this.setupEventListeners();
            this.initializeCharts();
            
            await this.loadInitialData();
            
            this.startAutoRefresh();
            
            console.log('✅ VyuhMitra Dashboard initialized successfully');
            
        } catch (error) {
            console.error('❌ Dashboard initialization failed:', error);
            this.showError('Failed to initialize dashboard: ' + error.message);
        }
    }
    
    setupHeightManagement() {
        try {
            const updateHeight = () => {
                const vh = window.innerHeight * 0.01;
                document.documentElement.style.setProperty('--vh', `${vh}px`);
                
                const dashboardMain = document.querySelector('.dashboard-main');
                if (dashboardMain) {
                    const headerHeight = 80;
                    const maxHeight = window.innerHeight - headerHeight;
                    dashboardMain.style.maxHeight = `${maxHeight}px`;
                }
            };
            
            updateHeight();
            window.addEventListener('resize', updateHeight);
            window.addEventListener('orientationchange', updateHeight);
            
            console.log('✅ Height management setup completed');
            
        } catch (error) {
            console.error('❌ Height management setup failed:', error);
        }
    }
    
    async loadInitialData() {
        try {
            console.log('🔄 Loading initial dashboard data...');
            console.log('🔍 [DEBUG] API Base URL:', this.apiBaseUrl);
            
            // Switch to table view by default to show train data
            this.switchToTableView();
            
            await this.refreshData();
        } catch (error) {
            console.error('❌ Failed to load initial data:', error);
            console.error('🔍 [DEBUG] Error details:', error);
            this.showError('Initial load failed. Live data unavailable.');
        }
    }
    
    switchToTableView() {
        console.log('🔍 [DEBUG] Switching to table view...');
        
        // Hide timeline view
        const timelineView = document.getElementById('timeline-view');
        const tableView = document.getElementById('table-view');
        const timelineBtn = document.querySelector('[data-view="timeline"]');
        const tableBtn = document.querySelector('[data-view="table"]');
        
        console.log('🔍 [DEBUG] Found elements:', {
            timelineView: !!timelineView,
            tableView: !!tableView,
            timelineBtn: !!timelineBtn,
            tableBtn: !!tableBtn
        });
        
        if (timelineView && tableView) {
            timelineView.classList.remove('active');
            tableView.classList.add('active');
            console.log('🔍 [DEBUG] Views switched successfully');
            console.log('🔍 [DEBUG] Timeline view classes:', timelineView.className);
            console.log('🔍 [DEBUG] Table view classes:', tableView.className);
        } else {
            console.log('🔍 [DEBUG] Could not find view elements');
        }
        
        if (timelineBtn && tableBtn) {
            timelineBtn.classList.remove('active');
            tableBtn.classList.add('active');
            console.log('🔍 [DEBUG] Buttons updated successfully');
        } else {
            console.log('🔍 [DEBUG] Could not find button elements');
        }
        
        // Check if table body exists
        const tableBody = document.getElementById('train-table-body');
        console.log('🔍 [DEBUG] Table body element found:', !!tableBody);
        if (tableBody) {
            console.log('🔍 [DEBUG] Table body current content:', tableBody.innerHTML.substring(0, 100) + '...');
        }
        
        console.log('🔍 [DEBUG] Table view should now be visible');
    }
    
    async refreshData() {
        if (this.isRefreshing) {
            console.log('⏳ Refresh already in progress, skipping...');
            return;
        }
        
        console.log('🔄 [DEBUG] Starting data refresh...');
        
        try {
            this.showLoadingState(true, 'Refreshing dashboard data...');
            
            // Updated API endpoints to match backend routes
            console.log('🔍 [DEBUG] Making API calls to endpoints with corrected URLs...');
            const results = await Promise.allSettled([
                this.fetchWithRetry('/api/dashboard/summary'),
                this.fetchWithRetry('/api/trains/schedule'),
                this.fetchWithRetry('/api/kpi/current'),
                this.fetchWithRetry('/api/abnormalities'),
                this.fetchWithRetry('/api/solutions/active')
            ]);
            
            console.log('🔍 [DEBUG] API call results:', results.map((r, i) => ({
                endpoint: ['/api/dashboard/summary', '/api/trains/schedule', '/api/kpi/current', '/api/abnormalities', '/api/solutions/active'][i],
                status: r.status,
                hasValue: r.status === 'fulfilled' && r.value !== undefined
            })));
            
            // Detailed debugging for each result
            results.forEach((result, index) => {
                const endpoint = ['/api/dashboard/summary', '/api/trains/schedule', '/api/kpi/current', '/api/abnormalities', '/api/solutions/active'][index];
                if (result.status === 'fulfilled') {
                    console.log(`✅ [DEBUG] ${endpoint} success:`, result.value);
                } else {
                    console.log(`❌ [DEBUG] ${endpoint} failed:`, result.reason);
                }
            });
            
            const [summaryResult, scheduleResult, kpiResult, abnormalitiesResult, solutionsResult] = results;
            
            let hasErrors = false;
            
            if (summaryResult.status === 'fulfilled' && summaryResult.value) {
                console.log('🔍 [DEBUG] Processing dashboard summary...', summaryResult.value);
                this.updateDashboardSummary(summaryResult.value);
            } else {
                console.warn('⚠️ Dashboard summary failed:', summaryResult.reason);
                hasErrors = true;
            }
            
            if (scheduleResult.status === 'fulfilled' && scheduleResult.value) {
                console.log('🔍 [DEBUG] Processing train schedule...', scheduleResult.value);
                this.updateTrainsSchedule(scheduleResult.value);
            } else {
                console.warn('⚠️ Train schedule fetch failed:', scheduleResult.reason);
                hasErrors = true;
            }
            
            if (kpiResult.status === 'fulfilled' && kpiResult.value) {
                this.updateKPIs(kpiResult.value);
            } else {
                console.warn('⚠️ KPI fetch failed:', kpiResult.reason);
                hasErrors = true;
            }
            
            if (abnormalitiesResult.status === 'fulfilled' && abnormalitiesResult.value) {
                this.updateAbnormalities(abnormalitiesResult.value);
            } else {
                console.warn('⚠️ Abnormalities fetch failed:', abnormalitiesResult.reason);
                hasErrors = true;
            }
            
            if (solutionsResult.status === 'fulfilled' && solutionsResult.value) {
                this.updateActiveSolutions(solutionsResult.value);
            } else {
                console.warn('⚠️ Solutions fetch failed:', solutionsResult.reason);
                hasErrors = true;
            }
            
            if (hasErrors) {
                this.retryCount++;
                if (this.retryCount >= this.maxRetries) {
                    console.warn('🔄 Multiple API failures. No fallback will be loaded.');
                    this.showError('Multiple API failures. Please check server logs and API key.');
                }
            } else {
                this.retryCount = 0;
            }
            
            console.log('📊 Dashboard data refresh completed');
            
        } catch (error) {
            console.error('❌ Data refresh failed:', error);
            this.handleRefreshError(error);
        } finally {
            this.isRefreshing = false;
            this.showLoadingState(false);
        }
    }
    
    async fetchWithRetry(endpoint, options = {}, timeout = 10000) {
        const maxAttempts = 3;
        let lastError;
        
        console.log(`🔍 [DEBUG] Fetching ${endpoint} (attempt 1/${maxAttempts})`);
        
        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                const fullUrl = `${this.apiBaseUrl}${endpoint}`;
                console.log(`🔍 [DEBUG] Making request to: ${fullUrl}`);
                
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), timeout);
                
                const response = await fetch(fullUrl, {
                    ...options,
                    signal: controller.signal,
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    }
                });
                
                clearTimeout(timeoutId);
                console.log(`🔍 [DEBUG] Response status: ${response.status} ${response.statusText}`);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const responseData = await response.json();
                console.log(`🔍 [DEBUG] Response data for ${endpoint}:`, responseData);
                
                // Handle the API response format which includes success, data, error, and timestamp
                if (responseData && responseData.success === true && responseData.data) {
                    console.log(`🔍 [DEBUG] Returning data property from response`);
                    return responseData.data;
                } else if (responseData && responseData.success === false) {
                    throw new Error(responseData.error || 'API returned success=false');
                } else {
                    // If the response doesn't match our expected format, return it as is
                    return responseData;
                }
                
            } catch (error) {
                lastError = error;
                console.warn(`⚠️ Attempt ${attempt}/${maxAttempts} failed for ${endpoint}:`, error.message);
                
                if (attempt < maxAttempts) {
                    const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
                    await this.sleep(delay);
                }
            }
        }
        
        throw lastError;
    }
    
    handleRefreshError(error) {
        this.retryCount++;
        
        if (this.retryCount >= this.maxRetries) {
            this.showError('Unable to connect to server. Live data unavailable.');
        } else {
            console.log(`⚠️ Refresh failed (${this.retryCount}/${this.maxRetries}), will retry...`);
        }
    }
    
    loadFallbackData() {
        // Disabled: No dummy data must be shown. Keep UI in error state instead.
        console.warn('Fallback data disabled: live data unavailable.');
        return;
        
        const fallbackData = {
            summary: {
                section_name: 'GY to GTL',
                section_info: {
                    name: 'GY to GTL',
                    total_trains: 8,
                    live_trains_entry: 2,
                    live_trains_exit: 1
                },
                performance_metrics: {
                    planned_throughput: 3.2,
                    efficiency_score: 78.5,
                    efficiency_grade: 'B+'
                },
                abnormalities: {
                    current_count: 1,
                    active_solutions: 0
                },
                last_updated: new Date().toLocaleTimeString()
            },
            kpis: {
                kpi_data: {
                    basic_stats: {
                        total_trains_scheduled: 8,
                        live_trains_tracked: 3,
                        data_coverage_percentage: 75
                    },
                    throughput_metrics: {
                        planned_throughput_trains_per_hour: 3.2
                    },
                    efficiency_metrics: {
                        on_time_performance_percentage: 78.5,
                        average_delay_minutes: 12.5,
                        schedule_reliability_score: 82.0
                    },
                    efficiency_score: {
                        overall_score: 78.5,
                        grade: 'B+'
                    }
                }
            },
            trains: {
                schedule_data: [
                    {
                        train_id: '12345',
                        train_name: 'Gooty-Guntakal Express',
                        status: 'Running',
                        delay_minutes: 15,
                        current_location: 'En Route'
                    },
                    {
                        train_id: '12346',
                        train_name: 'Local Passenger',
                        status: 'On Time',
                        delay_minutes: 0,
                        current_location: 'Scheduled'
                    },
                    {
                        train_id: '12347',
                        train_name: 'Southern Express',
                        status: 'Running',
                        delay_minutes: 8,
                        current_location: 'Approaching GTL'
                    }
                ]
            },
            abnormalities: {
                abnormalities: [
                    {
                        train_number: '12345',
                        type: 'delay',
                        severity: 'medium',
                        delay_minutes: 15,
                        description: 'Train 12345 delayed by 15 minutes due to signal issues'
                    }
                ]
            },
            solutions: {
                solutions: []
            }
        };
        
        this.updateDashboardSummary(fallbackData.summary);
        this.updateKPIs(fallbackData.kpis);
        this.updateTrainsSchedule(fallbackData.trains);
        this.updateAbnormalities(fallbackData.abnormalities);
        this.updateActiveSolutions(fallbackData.solutions);
        
        this.updateChartsWithDemoData();
        
        console.log('📊 Fallback data loaded successfully');
    }
    
    updateDashboardSummary(data) {
        try {
            console.log('🔍 [DEBUG] Updating dashboard summary with data:', data);
            const summary = data.summary || data;
            console.log('🔍 [DEBUG] Summary object:', summary);
            
            if (summary.status === 'no_active_trains') {
                this.updateElement('#section-name', summary.section + ' (Quiet Section)');
                this.showNotification(summary.message, 'info');
            }
            
            this.updateElement('#section-name', 
                summary.section_info?.name || summary.section_name || 'GY-GTL');
            this.updateElement('#last-updated', 
                summary.last_updated || new Date().toLocaleTimeString());
            
            const sectionInfo = summary.section_info || {};
            this.updateElement('#total-trains', sectionInfo.total_trains || 0);
            this.updateElement('#active-trains', sectionInfo.live_trains_entry || 0);
            
            const performance = summary.performance_metrics || {};
            this.updateElement('#efficiency-score', 
                `${performance.efficiency_score || 0}%`);
            
            const abnormalities = summary.abnormalities || {};
            this.updateElement('#abnormalities-count', abnormalities.current_count || 0);
            
        } catch (error) {
            console.error('❌ Error updating dashboard summary:', error);
        }
    }
    
    updateKPIs(data) {
        try {
            const kpiData = data.kpi_data || data;
            
            const basicStats = kpiData.basic_stats || {};
            this.updateElement('#total-trains', basicStats.total_trains_scheduled || 0);
            
            const throughputMetrics = kpiData.throughput_metrics || {};
            this.updateElement('#throughput', 
                `${throughputMetrics.planned_throughput_trains_per_hour || 0}`);
            
            const efficiencyMetrics = kpiData.efficiency_metrics || {};
            this.updateElement('#kpi-on-time', 
                `${efficiencyMetrics.on_time_performance_percentage || 0}%`);
            this.updateElement('#kpi-avg-delay', 
                `${efficiencyMetrics.average_delay_minutes || 0} min`);
            
            const efficiencyScore = kpiData.efficiency_score || {};
            this.updateElement('#efficiency-score', 
                `${efficiencyScore.overall_score || 0}%`);
            
            this.updateCharts(kpiData);
            
        } catch (error) {
            console.error('❌ Error updating KPIs:', error);
        }
    }
    
    updateTrainsSchedule(data) {
        try {
            console.log('🔍 [DEBUG] Updating trains schedule with data:', data);
            const trainsList = document.getElementById('train-table-body');
            if (!trainsList) {
                console.log('🔍 [DEBUG] train-table-body element not found, looking for alternatives...');
                // Try alternative selectors
                const alternatives = ['trains-list', 'schedule-container', 'trains-container'];
                for (const selector of alternatives) {
                    const element = document.getElementById(selector);
                    if (element) {
                        console.log(`🔍 [DEBUG] Found alternative element: ${selector}`);
                        break;
                    }
                }
                return;
            }
            
            const scheduleData = data.schedule_data || data || [];
            console.log('🔍 [DEBUG] Schedule data:', scheduleData);
            
            if (!scheduleData || scheduleData.length === 0) {
                console.log('🔍 [DEBUG] No schedule data available');
                trainsList.innerHTML = '<tr><td colspan="8" class="loading">No train data available</td></tr>';
                return;
            }
            
            const trainRowsHtml = scheduleData.map(train => `
                <tr class="train-row" data-train="${train.train_id}">
                    <td class="train-id">${train.train_id || 'Unknown'}</td>
                    <td class="train-name">${train.train_name || 'Unknown Train'}</td>
                    <td class="static-entry">${train.static_entry || 'N/A'}</td>
                    <td class="optimized-entry">${train.optimized_entry || 'N/A'}</td>
                    <td class="deviation">${train.delay_minutes ? `${train.delay_minutes}min` : '0min'}</td>
                    <td class="status">
                        <span class="status-badge ${this.getStatusClass(train.status, train.delay_minutes)}">${train.status || 'Unknown'}</span>
                    </td>
                    <td class="platform">${train.platform || 'TBD'}</td>
                    <td class="actions">
                        <button class="btn-small" onclick="dashboard.showTrainDetails('${train.train_id}')">View</button>
                    </td>
                </tr>
            `).join('');
            
            console.log('🔍 [DEBUG] Setting innerHTML with train rows...');
            trainsList.innerHTML = trainRowsHtml;
            console.log('🔍 [DEBUG] innerHTML set, checking if rows were added...');
            console.log('🔍 [DEBUG] Number of train rows in DOM:', trainsList.querySelectorAll('.train-row').length);
            
            trainsList.querySelectorAll('.train-row').forEach((item, index) => {
                console.log(`🔍 [DEBUG] Adding click listener to train row ${index + 1}`);
                item.addEventListener('click', (e) => {
                    const trainNumber = e.currentTarget.dataset.train;
                    console.log(`🔍 [DEBUG] Train row clicked: ${trainNumber}`);
                    this.showTrainDetails(trainNumber);
                });
            });
            
            console.log('🔍 [DEBUG] Train schedule update completed successfully');
            
        } catch (error) {
            console.error('❌ Error updating trains schedule:', error);
            console.error('🔍 [DEBUG] Full error details:', error);
        }
    }
    
    updateAbnormalities(data) {
        try {
            const abnormalitiesList = document.getElementById('abnormalities-list');
            if (!abnormalitiesList) return;
            
            if (data.message && data.status === 'no_active_trains') {
                abnormalitiesList.innerHTML = `<div class="info-state">${data.message}</div>`;
                const abnormalities = data.abnormalities || [];
                if (abnormalities.length > 0) {
                    abnormalitiesList.innerHTML += abnormalities.map(ab => `
                        <div class="abnormality-item predicted">
                            <p>${ab.description} (What-If Prediction)</p>
                            <button onclick="dashboard.runScenario('weather_disruption')">Run What-If</button>
                        </div>
                    `).join('');
                }
                return;
            }
            
            const abnormalities = data.abnormalities || data || [];
            
            if (!abnormalities || abnormalities.length === 0) {
                abnormalitiesList.innerHTML = '<div class="empty-state">No abnormalities detected</div>';
                return;
            }
            
            const abnormalityItemsHtml = abnormalities.map(abnormality => `
                <div class="abnormality-item ${abnormality.severity || 'medium'}">
                    <div class="abnormality-content">
                        <div class="abnormality-header">
                            <span class="abnormality-train">Train ${abnormality.train_number}</span>
                            <span class="abnormality-type">${abnormality.type || 'Issue'}</span>
                        </div>
                        <div class="abnormality-description">${abnormality.description || 'No description'}</div>
                    </div>
                    <div class="abnormality-actions">
                        <button class="btn btn-primary btn-sm" onclick="dashboard.generateSolutions('${abnormality.train_number}')">
                            🤖 Generate Solutions
                        </button>
                    </div>
                </div>
            `).join('');
            
            abnormalitiesList.innerHTML = abnormalityItemsHtml;
            
        } catch (error) {
            console.error('❌ Error updating abnormalities:', error);
            }
    }

    // ----- Added utility and stub methods for reliability and logging -----
    setupEventListeners() {
        try {
            const refreshBtn = document.getElementById('refresh-btn');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', () => {
                    console.info('[UI] Refresh button clicked');
                    this.refreshData();
                });
            }
            console.info('[UI] Event listeners set up');
        } catch (e) {
            console.error('[UI] setupEventListeners error', e);
        }
    }

    initializeCharts() {
        // Charts are optional; ensure this never blocks initialization
        console.info('[UI] initializeCharts called');
    }

    showError(message) {
        console.error('[UI] ERROR:', message);
        // Surface in header status if available
        const el = document.getElementById('system-status');
        if (el) {
            el.textContent = `Error: ${message}`;
            el.classList.add('error');
        }
    }

    showLoadingState(isLoading, text = '') {
        const btn = document.getElementById('refresh-btn');
        if (btn) {
            btn.disabled = !!isLoading;
            btn.textContent = isLoading ? (text || 'Loading...') : '🔄 Refresh Data';
        }
        const last = document.getElementById('last-update');
        if (!isLoading && last) {
            last.textContent = new Date().toLocaleTimeString();
        }
    }

    updateElement(selector, value) {
        try {
            const el = document.querySelector(selector);
            if (el != null) el.textContent = String(value);
        } catch (e) {
            console.warn('[UI] updateElement failed', selector, e);
        }
    }

    // Start/stop periodic refresh
    startAutoRefresh() {
        try {
            if (this.refreshTimerId) {
                console.info('[UI] Auto-refresh already running');
                return;
            }
            this.refreshTimerId = setInterval(() => {
                console.debug('🔁 [DEBUG] Auto-refresh tick');
                this.refreshData();
            }, this.refreshInterval);
            console.info('[UI] Auto-refresh started (interval =', this.refreshInterval, 'ms)');
        } catch (e) {
            console.error('[UI] startAutoRefresh error', e);
        }
    }

    stopAutoRefresh() {
        try {
            if (this.refreshTimerId) {
                clearInterval(this.refreshTimerId);
                this.refreshTimerId = null;
                console.info('[UI] Auto-refresh stopped');
            }
        } catch (e) {
            console.error('[UI] stopAutoRefresh error', e);
        }
    }

    sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

    getStatusClass(status, delay) {
        if (status && /live|running/i.test(status)) return 'status-live';
        if ((delay || 0) > 10) return 'status-delayed';
        return 'status-scheduled';
    }

    updateCharts(kpiData) {
        // Hook for charts.js integration; non-blocking
        console.info('[UI] updateCharts called');
    }

    updateActiveSolutions(data) {
        try {
            const count = (data && data.count) || (data && data.solutions && data.solutions.length) || 0;
            const el = document.getElementById('active-solutions-count');
            if (el) el.textContent = String(count);
        } catch (e) {
            console.error('[UI] updateActiveSolutions error', e);
        }
    }

    async generateSolutions(trainNumber) {
        try {
            console.info('[UI] generateSolutions', trainNumber);
            const res = await fetch(`${this.apiBaseUrl}/solutions/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ train_id: trainNumber })
            });
            const body = await res.text();
            console.info('[UI] generateSolutions response', res.status, body.slice(0, 300));
        } catch (e) {
            console.error('[UI] generateSolutions failed', e);
        }
    }

    showTrainDetails(trainNumber) {
        console.info('[UI] showTrainDetails', trainNumber);
        // Placeholder: could open modal populated from schedule/live endpoints
    }
}

// Bootstrap: instantiate dashboard when DOM is ready
(function () {
    if (typeof window !== 'undefined') {
        // Diagnostic: capture any runtime errors and promise rejections
        window.addEventListener('error', function (e) {
            try { console.error('[UI] window.onerror', e.message || e); } catch (_) {}
        });
        window.addEventListener('unhandledrejection', function (e) {
            try { console.error('[UI] unhandledrejection', e.reason || e); } catch (_) {}
        });
        window.addEventListener('DOMContentLoaded', function () {
            try {
                window.dashboard = new VyuhMitraDashboard();
                console.info('[UI] Dashboard instantiated');
            } catch (e) {
                console.error('[UI] Failed to start dashboard', e);
            }
        });
    }
})();
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
            this.setupScenarioHandlers();
            
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
            // Ensure only table is visible for screen readers and layout
            timelineView.setAttribute('hidden', 'true');
            tableView.removeAttribute('hidden');
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
    
    switchToTimelineView() {
        console.log('🔍 [DEBUG] Switching to timeline view...');
        const timelineView = document.getElementById('timeline-view');
        const tableView = document.getElementById('table-view');
        const timelineBtn = document.querySelector('[data-view="timeline"]');
        const tableBtn = document.querySelector('[data-view="table"]');
        if (timelineView && tableView) {
            tableView.classList.remove('active');
            timelineView.classList.add('active');
            // Ensure only timeline is visible
            tableView.setAttribute('hidden', 'true');
            timelineView.removeAttribute('hidden');
        }
        if (timelineBtn && tableBtn) {
            tableBtn.classList.remove('active');
            timelineBtn.classList.add('active');
        }
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
            // Save last KPI snapshot for What-If baseline
            this._lastKpi = data && data.kpi_data ? data : { kpi_data: kpiData };
            
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
            // cache for simulation and timeline
            this._scheduleCache = Array.isArray(scheduleData) ? scheduleData : [];
            
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
            // View toggles
            const timelineBtn = document.getElementById('schedule-view-btn');
            const tableBtn = document.getElementById('table-view-btn');
            if (timelineBtn) timelineBtn.addEventListener('click', () => this.switchToTimelineView());
            if (tableBtn) tableBtn.addEventListener('click', () => this.switchToTableView());
            // Quick simulate button in schedule controls
            const simulateBtn = document.getElementById('simulation-btn');
            if (simulateBtn) simulateBtn.addEventListener('click', () => this.startSimulation());
            // Simulation panel controls
            const playBtn = document.getElementById('play-simulation');
            const pauseBtn = document.getElementById('pause-simulation');
            const resetBtn = document.getElementById('reset-simulation');
            if (playBtn) playBtn.addEventListener('click', () => this.startSimulation());
            if (pauseBtn) pauseBtn.addEventListener('click', () => this.pauseSimulation());
            if (resetBtn) resetBtn.addEventListener('click', () => this.resetSimulation());
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
            const solutions = (data && data.solutions) || [];
            const count = data && typeof data.count === 'number' ? data.count : solutions.length;
            const countEl = document.getElementById('active-solutions-count');
            if (countEl) countEl.textContent = String(count);

            const list = document.getElementById('solutions-list');
            if (!list) return;

            if (!solutions.length) {
                list.innerHTML = `
                    <div class="no-solutions">
                        <div class="ai-icon">🧠</div>
                        <p>AI monitoring for optimal solutions...</p>
                    </div>`;
                return;
            }
            // Normalize backend fields to UI metrics
            list.innerHTML = solutions.map((s, idx) => {
                const title = s.title || s.name || s.way_type || `Solution #${idx + 1}`;
                const desc = s.description || s.narrative || 'No description provided';
                const prio = (s.priority || (s.feasibility_score >= 80 ? 'high' : s.feasibility_score >= 65 ? 'medium' : 'low')).toLowerCase();
                const metrics = s.metrics || {};
                const throughput = (metrics.throughput_gain_per_hour ?? metrics.throughput_gain ?? s.kpi_impact?.throughput_change ?? 0);
                const delay = (metrics.delay_reduction_minutes ?? metrics.delay_reduction ?? Math.max(0, s.time_recovery_minutes ?? 0));
                const safety = (metrics.safety_score ?? metrics.risk_score ?? s.safety_score ?? 0);
                const id = s.id || s.solution_id || `sol_${idx}`;
                return `
                    <div class="solution-item" data-solution-id="${id}">
                        <div class="solution-header">
                            <div class="solution-title">${title}</div>
                            <div class="solution-priority ${prio}">${prio.toUpperCase()}</div>
                        </div>
                        <div class="solution-details">${desc}</div>
                        <div class="solution-metrics">
                            <div class="solution-metric">
                                <div class="solution-metric-value">+${Number(throughput).toFixed(2)}</div>
                                <div class="solution-metric-label">Trains/Hr</div>
                            </div>
                            <div class="solution-metric">
                                <div class="solution-metric-value">-${Number(delay).toFixed(1)}m</div>
                                <div class="solution-metric-label">Avg Delay</div>
                            </div>
                            <div class="solution-metric">
                                <div class="solution-metric-value">${Number(safety).toFixed(0)}%</div>
                                <div class="solution-metric-label">Safety Score</div>
                            </div>
                        </div>
                        <div class="solution-actions">
                            <button class="accept-btn" data-action="accept" data-solution-id="${id}">✅ Accept</button>
                            <button class="reject-btn" data-action="reject" data-solution-id="${id}">❌ Reject</button>
                            <button class="view-details-btn" data-action="adjust" data-solution-id="${id}">✏️ Adjust</button>
                        </div>
                    </div>`;
            }).join('');

            // Wire buttons
            list.querySelectorAll('[data-action]')
                .forEach(btn => btn.addEventListener('click', (e) => {
                    const action = e.currentTarget.getAttribute('data-action');
                    const solutionId = e.currentTarget.getAttribute('data-solution-id');
                    const card = e.currentTarget.closest('.solution-item');
                    const title = card?.querySelector('.solution-title')?.textContent || 'Solution Details';
                    if (action === 'adjust') {
                        this.openSolutionModal(solutionId, title, card?.outerHTML || '');
                    } else {
                        this.submitSolutionFeedback({ solution_id: solutionId, decision: action });
                    }
                }));

        } catch (e) {
            console.error('[UI] updateActiveSolutions error', e);
        }
    }

    async generateSolutions(trainNumber) {
        try {
            console.info('[UI] generateSolutions', trainNumber);
            // Prompt for optional reason from controller; empty means let ML infer
            let reason = '';
            try { reason = window.prompt('Optional: provide reason for delay/issue (leave blank to let AI infer):', '') || ''; } catch(_) {}
            // Disable duplicate clicks during request
            const disable = (on) => { try { document.querySelectorAll('[onclick*="generateSolutions"]').forEach(b => b.disabled = !!on); } catch(_) {} };
            disable(true);
            const payload = { train_id: trainNumber };
            if (reason.trim()) payload.reason = reason.trim();
            await this.fetchWithRetry('/api/solutions/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            }, 20000);
            console.info('[UI] generateSolutions response OK');
            // Refresh active solutions list after generation
            await this.refreshSpecific('solutions');
            // Wire buttons
            const list = document.getElementById('solutions-list');
            if (list) {
                list.querySelectorAll('[data-action]')
                    .forEach(btn => btn.addEventListener('click', (e) => {
                        const action = e.currentTarget.getAttribute('data-action');
                        const solutionId = e.currentTarget.getAttribute('data-solution-id');
                        const card = e.currentTarget.closest('.solution-item');
                        const title = card?.querySelector('.solution-title')?.textContent || 'Solution Details';
                        if (action === 'adjust') {
                            this.openSolutionModal(solutionId, title, card?.outerHTML || '');
                        } else {
                            this.submitSolutionFeedback({ solution_id: solutionId, decision: action });
                        }
                    }));
            }
            disable(false);
        } catch (e) {
            console.error('[UI] generateSolutions failed', e);
            try { document.querySelectorAll('[onclick*="generateSolutions"]').forEach(b => b.disabled = false); } catch(_) {}
        }
    }

    async showTrainDetails(trainNumber) {
        try {
            console.info('[UI] showTrainDetails', trainNumber);
            // Prevent concurrent detail requests
            if (this._detailsLoading) return;
            this._detailsLoading = true;
            const data = await this.fetchWithRetry(`/api/train/${encodeURIComponent(trainNumber)}/details`, {}, 20000);
            const modal = document.getElementById('solution-modal');
            if (!modal) return;
            modal.style.display = 'block';
            const set = (sel, fn) => { const el = modal.querySelector(sel); if (el) fn(el); };
            set('#modal-title', el => el.textContent = `Train ${trainNumber} Details`);
            const d = data || {};
            const train = d.train || {};
            const route = Array.isArray(d.route) ? d.route.slice(0, 10) : [];
            const rows = route.map((r, i) => {
                const st = r.station || {};
                const arr = r.scheduledArrival ?? r.schedule?.arrival ?? r.actualArrival ?? '';
                const dep = r.scheduledDeparture ?? r.schedule?.departure ?? r.actualDeparture ?? '';
                const plat = r.platform ?? r.livePlatform ?? '';
                const delayA = r.delayArrivalMinutes ?? '';
                const delayD = r.delayDepartureMinutes ?? '';
                return `<tr>
                    <td>${i+1}</td><td>${st.code || r.stationCode || ''}</td>
                    <td>${st.name || r.stationName || ''}</td>
                    <td>${arr}</td><td>${dep}</td>
                    <td>${plat}</td>
                    <td>${delayA || delayD || ''}</td>
                </tr>`;
            }).join('');
            set('#modal-body', el => el.innerHTML = `
                <div class="table">
                    <div><strong>Status:</strong> ${d.status || 'Unknown'} | <strong>Delay:</strong> ${d.overall_delay_minutes || 0} min | <strong>Updated:</strong> ${d.last_updated || '-'}</div>
                    <div><strong>Current:</strong> ${d.current_location || '-'} | <strong>Date:</strong> ${d.journey_date || '-'}</div>
                </div>
                <div class="table-wrapper" style="max-height:240px;overflow:auto;margin-top:8px;">
                    <table class="data-table">
                        <thead>
                            <tr><th>#</th><th>Code</th><th>Station</th><th>Sch Arr</th><th>Sch Dep</th><th>Plat</th><th>Delay</th></tr>
                        </thead>
                        <tbody>${rows || '<tr><td colspan="7">No route data</td></tr>'}</tbody>
                    </table>
                </div>
            `);
            // repurpose footer buttons
            const accept = modal.querySelector('#modal-accept');
            const reject = modal.querySelector('#modal-reject');
            const adjustAccept = modal.querySelector('#modal-adjust-accept');
            const closeBtn = modal.querySelector('#modal-close');
            const xBtn = modal.querySelector('.close-modal');
            const close = () => modal.style.display = 'none';
            if (accept) accept.onclick = close;
            if (reject) reject.onclick = close;
            if (adjustAccept) adjustAccept.onclick = close;
            if (closeBtn) closeBtn.onclick = close; if (xBtn) xBtn.onclick = close;
        } catch (e) {
            console.error('[UI] showTrainDetails failed', e);
        } finally {
            this._detailsLoading = false;
        }
    }

    // ----- Modal + Feedback Wiring -----
    openSolutionModal(solutionId, title, contentHtml) {
        const modal = document.getElementById('solution-modal');
        if (!modal) return;
        modal.style.display = 'block';
        const set = (sel, fn) => { const el = modal.querySelector(sel); if (el) fn(el); };
        set('#modal-title', el => el.textContent = title);
        set('#modal-body', el => el.innerHTML = `
            <div class="alert">Adjust parameters and confirm your decision.</div>
            <div class="table">
                <div>Solution ID: <strong>${solutionId}</strong></div>
            </div>
            ${contentHtml}
        `);
        const accept = modal.querySelector('#modal-accept');
        const reject = modal.querySelector('#modal-reject');
        const adjustAccept = modal.querySelector('#modal-adjust-accept');
        const closeBtn = modal.querySelector('#modal-close');
        const xBtn = modal.querySelector('.close-modal');
        const close = () => modal.style.display = 'none';
        const commit = (decision) => {
            this.submitSolutionFeedback({ solution_id: solutionId, decision });
            close();
        };
        accept.onclick = () => commit('accept');
        reject.onclick = () => commit('reject');
        if (adjustAccept) {
            adjustAccept.onclick = () => {
                this.submitSolutionFeedback({ solution_id: solutionId, decision: 'accept', adjusted: true });
                close();
            };
        }
        closeBtn.onclick = close; xBtn.onclick = close;
    }

    async submitSolutionFeedback(payload) {
        try {
            console.info('[UI] submitSolutionFeedback', payload);
            const res = await fetch(`${this.apiBaseUrl}/api/solutions/feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const body = await res.text();
            console.info('[UI] feedback response', res.status, body.slice(0, 300));
            await this.refreshSpecific('solutions');
        } catch (e) {
            console.error('[UI] submitSolutionFeedback failed', e);
        }
    }

    async refreshSpecific(which) {
        try {
            if (which === 'solutions') {
                const res = await this.fetchWithRetry('/api/solutions/active');
                this.updateActiveSolutions(res);
            }
        } catch (e) {
            console.error('[UI] refreshSpecific failed', which, e);
        }
    }

    // ----- What-If Scenario Analysis -----
    setupScenarioHandlers() {
        try {
            const container = document.querySelector('.what-if-analysis');
            if (!container) return;
            container.querySelectorAll('.scenario-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const scenario = btn.dataset.scenario || 'custom';
                    const customDelay = Number(document.getElementById('custom-delay')?.value || 0);
                    this.runScenario(scenario, { delay: customDelay });
                });
            });
            console.info('[UI] What-If handlers attached');
        } catch (e) {
            console.error('[UI] setupScenarioHandlers failed', e);
        }
    }

    runScenario(scenario, params = {}) {
        try {
            // Use current KPI as baseline
            const base = this._lastKpi || { kpi_data: { throughput_metrics: {}, efficiency_metrics: {}, efficiency_score: {} } };
            const metrics = base.kpi_data || {};
            const throughput = metrics.throughput_metrics?.planned_throughput_trains_per_hour || 0;
            const effPct = metrics.efficiency_metrics?.on_time_performance_percentage || 0;
            const avgDelay = metrics.efficiency_metrics?.average_delay_minutes || 0;

            // Simple deterministic impacts per scenario, bounded and safe; no live data mutation
            let delta = { throughput: 0, eff: 0, delay: 0 };
            switch (scenario) {
                case 'reduce_headway':
                    delta = { throughput: +0.5, eff: +2, delay: -1.0 }; break;
                case 'weather_disruption':
                    delta = { throughput: -0.3, eff: -5, delay: +4.0 }; break;
                case 'add_delay':
                    delta = { throughput: -0.2, eff: -3, delay: +6.0 }; break;
                case 'emergency':
                    delta = { throughput: -1.0, eff: -10, delay: +10.0 }; break;
                default: // custom
                    delta = { throughput: -Math.min(params.delay || 0, 60) * 0.01, eff: -(params.delay || 0) * 0.2, delay: +(params.delay || 0) };
            }

            const res = {
                scenario,
                before: { throughput, effPct, avgDelay },
                after: {
                    throughput: Math.max(0, throughput + delta.throughput),
                    effPct: Math.max(0, Math.min(100, effPct + delta.eff)),
                    avgDelay: Math.max(0, avgDelay + delta.delay)
                },
                delta
            };

            this.renderScenarioResult(res);
        } catch (e) {
            console.error('[UI] runScenario failed', e);
        }
    }

    renderScenarioResult(result) {
        const tgt = document.getElementById('what-if-result');
        if (!tgt) return;
        const tag = (x) => `<span style="font-weight:600">${x}</span>`;
        tgt.innerHTML = `
            <div class="fade-in">
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:10px;">
                    <div class="alert">
                        <div>Throughput</div>
                        <div>Before: ${tag(result.before.throughput.toFixed(2))} → After: ${tag(result.after.throughput.toFixed(2))} (${result.delta.throughput>=0?'+':''}${result.delta.throughput.toFixed(2)})</div>
                    </div>
                    <div class="alert">
                        <div>On-Time %</div>
                        <div>Before: ${tag(result.before.effPct.toFixed(0))}% → After: ${tag(result.after.effPct.toFixed(0))}% (${result.delta.eff>=0?'+':''}${result.delta.eff.toFixed(0)}%)</div>
                    </div>
                    <div class="alert ${result.delta.delay>0?'error':''}">
                        <div>Average Delay</div>
                        <div>Before: ${tag(result.before.avgDelay.toFixed(1))}m → After: ${tag(result.after.avgDelay.toFixed(1))}m (${result.delta.delay>=0?'+':''}${result.delta.delay.toFixed(1)}m)</div>
                    </div>
                </div>
                <div class="alert">Scenario: <strong>${result.scenario}</strong>. This is a non-destructive analysis. Live data is unaffected.</div>
            </div>`;
    }

    // ----- Simulation -----
    startSimulation() {
        try {
            if (!Array.isArray(this._scheduleCache) || this._scheduleCache.length === 0) {
                console.warn('[SIM] No schedule to simulate');
                return;
            }
            const speedSel = document.getElementById('simulation-speed-control');
            this._simSpeed = Number(speedSel?.value || 1);
            if (this._simTime == null) {
                // Start at the nearest active window midpoint so trains are visible quickly
                const windows = this._scheduleCache.map(t => ({
                    s: (t.static_entry||0) + (t.delay_minutes||0),
                    e: (t.static_exit||0) + (t.delay_minutes||0)
                })).filter(w => w.e > w.s);
                if (windows.length) {
                    windows.sort((a,b) => (a.s - b.s));
                    const first = windows[0];
                    this._simTime = first.s + Math.min(5, (first.e - first.s)/2);
                } else {
                    this._simTime = this._scheduleCache.reduce((min, t) => Math.min(min, t.static_entry||0), Infinity) || 360;
                }
            }
            if (this._simTimer) cancelAnimationFrame(this._simTimer);
            this.simulationRunning = true;
            const tick = () => {
                if (!this.simulationRunning) return;
                this._simulationTick();
                this._simTimer = requestAnimationFrame(tick);
            };
            tick();
        } catch (e) { console.error('[SIM] start failed', e); }
    }

    pauseSimulation() {
        this.simulationRunning = false;
    }

    resetSimulation() {
        this.simulationRunning = false;
        this._simTime = undefined;
        this._drawSimulationFrame();
        const timeEl = document.getElementById('simulation-time');
        if (timeEl) timeEl.textContent = '06:00';
        const actEl = document.getElementById('simulation-active');
        if (actEl) actEl.textContent = '0';
        const thrEl = document.getElementById('simulation-throughput');
        if (thrEl) thrEl.textContent = '0.0/hr';
    }

    _simulationTick() {
        // advance time and draw
        const dt = (1/60) * this._simSpeed; // minutes per frame ~ scaled
        this._simTime = (this._simTime || 360) + dt;
        this._drawSimulationFrame();
    }

    _fmtTime(mins) {
        const m = Math.max(0, Math.floor(mins));
        const h = Math.floor(m / 60) % 24; const mm = m % 60;
        return `${String(h).padStart(2,'0')}:${String(mm).padStart(2,'0')}`;
    }

    _drawSimulationFrame() {
        try {
            const canvas = document.getElementById('simulationCanvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            const W = canvas.width, H = canvas.height;
            ctx.clearRect(0,0,W,H);
            ctx.fillStyle = '#0b1220'; ctx.fillRect(0,0,W,H);
            // rails
            const tracks = Math.max(3, Math.min(10, (this._scheduleCache||[]).length));
            const trackGap = H / (tracks+1);
            ctx.strokeStyle = '#1f2937'; ctx.lineWidth = 2;
            for (let i=1;i<=tracks;i++){ ctx.beginPath(); ctx.moveTo(0, i*trackGap); ctx.lineTo(W, i*trackGap); ctx.stroke(); }

            const t0 = this._scheduleCache?.reduce((min,t)=>Math.min(min, t.static_entry||0), 1440) || 360;
            const t1 = this._scheduleCache?.reduce((max,t)=>Math.max(max, t.static_exit||0), 0) || 900;
            const span = Math.max(1, t1 - t0);
            const now = this._simTime || t0;
            const active = [];
            (this._scheduleCache||[]).forEach((tr, idx) => {
                const entry = (tr.static_entry||0) + (tr.delay_minutes||0);
                const exit = (tr.static_exit||0) + (tr.delay_minutes||0);
                const y = ((idx % tracks)+1) * trackGap;
                // draw schedule bar
                const x1 = ((entry - t0)/span)*W; const x2 = ((exit - t0)/span)*W;
                ctx.fillStyle = '#334155'; ctx.fillRect(x1, y-6, Math.max(2, x2-x1), 12);
                // draw train position if active
                if (now >= entry && now <= exit) {
                    const p = (now - entry) / Math.max(1,(exit-entry));
                    const x = x1 + p * Math.max(2,x2-x1);
                    const delayed = (tr.delay_minutes||0) > 10;
                    ctx.fillStyle = delayed ? '#f39c12' : '#27ae60';
                    ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI*2); ctx.fill();
                    ctx.fillStyle = '#e5e7eb'; ctx.font = '12px Inter, sans-serif';
                    ctx.fillText(String(tr.train_id), Math.min(W-40, x+8), y-8);
                    active.push(tr);
                }
            });

            const timeEl = document.getElementById('simulation-time');
            if (timeEl) timeEl.textContent = this._fmtTime(now);
            const actEl = document.getElementById('simulation-active');
            if (actEl) actEl.textContent = String(active.length);
            const thrEl = document.getElementById('simulation-throughput');
            if (thrEl) thrEl.textContent = `${(active.length/ (span/60)).toFixed(1)}/hr`;
        } catch (e) { console.error('[SIM] draw failed', e); }
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
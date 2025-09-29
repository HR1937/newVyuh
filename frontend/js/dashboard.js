/**
 * VyuhMitra Control Center - Professional Railway Control Interface
 * LIVE DATA ONLY with extensive logging and real-time updates
 */

class VyuhMitraControlCenter {
    constructor() {
        this.apiBaseUrl = 'http://127.0.0.1:5000';
        this.refreshInterval = 10000; // 10 seconds
        this.currentData = {};
        this.selectedSolution = null;
        this.manualMode = false;
        
        console.log('🚂 [CONTROL CENTER] Initializing VyuhMitra Control Center...');
        console.log('🔍 [LIVE DATA] API Base URL:', this.apiBaseUrl);
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeCharts();
        this.startDataRefresh();
        this.updateSystemStatus();
        
        console.log('✅ [CONTROL CENTER] Initialization complete');
    }

    setupEventListeners() {
        // Header controls
        document.getElementById('refresh-btn').addEventListener('click', () => this.forceRefresh());
        
        // View controls
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchView(e.target.dataset.view));
        });
        
        // AI Suggestions
        document.getElementById('accept-solution').addEventListener('click', () => this.acceptSolution());
        document.getElementById('adjust-solution').addEventListener('click', () => this.adjustSolution());
        document.getElementById('reject-solution').addEventListener('click', () => this.rejectSolution());
        
        // Scenario Simulator
        document.getElementById('run-simulation').addEventListener('click', () => this.runSimulation());
        
        // Manual Control
        document.getElementById('manual-mode').addEventListener('change', (e) => this.toggleManualMode(e.target.checked));
        document.getElementById('execute-manual').addEventListener('click', () => this.executeManualOverride());
        
        // Modals
        document.querySelectorAll('.close-modal').forEach(btn => {
            btn.addEventListener('click', () => this.closeModals());
        });
        
        console.log('🔗 [CONTROL CENTER] Event listeners attached');
    }

    async startDataRefresh() {
        console.log('🔄 [LIVE DATA] Starting continuous data refresh...');
        
        // Initial load
        await this.refreshAllData();
        
        // Set up interval
        setInterval(() => {
            this.refreshAllData();
        }, this.refreshInterval);
    }

    async refreshAllData() {
        console.log('📡 [LIVE DATA] Refreshing all data from server...');
        
        try {
            // Update system indicators
            this.updateIndicator('api-status', 'connecting');
            this.updateIndicator('data-feed', 'connecting');
            
            // Fetch all data in parallel
            const [summary, trains, kpis, abnormalities, solutions] = await Promise.all([
                this.fetchWithLogging('/api/dashboard/summary'),
                this.fetchWithLogging('/api/trains/schedule'),
                this.fetchWithLogging('/api/kpi/current'),
                this.fetchWithLogging('/api/abnormalities'),
                this.fetchWithLogging('/api/solutions/active')
            ]);
            
            // Update UI with live data
            this.updateSectionOverview(trains);
            this.updateAISuggestions(abnormalities, solutions);
            this.updateKPIDashboard(kpis);
            this.updateSystemIntegration(summary);
            
            // Update indicators
            this.updateIndicator('api-status', 'active');
            this.updateIndicator('data-feed', 'active');
            
            console.log('✅ [LIVE DATA] All data refreshed successfully');
            
        } catch (error) {
            console.error('❌ [LIVE DATA] Data refresh failed:', error);
            this.updateIndicator('api-status', 'error');
            this.updateIndicator('data-feed', 'error');
            this.showSystemAlert('Data refresh failed: ' + error.message);
        }
    }

    async fetchWithLogging(endpoint, method = 'GET', body = null) {
        const url = `${this.apiBaseUrl}${endpoint}`;
        console.log(`🔍 [API CALL] ${method} ${endpoint}`);
        
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            timeout: 15000
        };
        
        if (body && method !== 'GET') {
            options.body = JSON.stringify(body);
            console.log(`📤 [API BODY] ${endpoint} - Sending:`, body);
        }
        
        try {
            const response = await fetch(url, options);
            
            console.log(`📊 [API RESPONSE] ${endpoint} - Status: ${response.status}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            console.log(`✅ [API SUCCESS] ${endpoint} - Data received:`, {
                success: data.success,
                dataKeys: data.data ? Object.keys(data.data) : 'No data object',
                timestamp: data.timestamp
            });
            
            if (!data.success) {
                console.error(`❌ [API ERROR] ${endpoint} - Server returned error:`, data.error);
                throw new Error(data.error || 'Server returned unsuccessful response');
            }
            
            return data.data;
            
        } catch (error) {
            console.error(`💥 [API FAILED] ${endpoint} - Error:`, error);
            throw error;
        }
    }

    updateSectionOverview(trainsData) {
        console.log('🚉 [UI UPDATE] Updating section overview with live data...');
        
        if (!trainsData) {
            console.warn('⚠️ [UI UPDATE] No trains data available');
            return;
        }
        
        // Update section name
        const sectionName = trainsData.section || 'NDLS → AGC';
        document.getElementById('section-name').textContent = sectionName;
        
        // Update trains table
        const tableBody = document.getElementById('trains-table-body');
        tableBody.innerHTML = '';
        
        const schedules = trainsData.static_schedules || {};
        const liveData = trainsData.live_data || {};
        
        console.log(`🚂 [TRAINS DATA] Processing ${Object.keys(schedules).length} trains`);
        
        if (Object.keys(schedules).length === 0) {
            tableBody.innerHTML = '<tr><td colspan="8" class="no-data">❌ No live train data available</td></tr>';
            console.error('❌ [TRAINS DATA] No train schedules found in response');
            return;
        }
        
        Object.entries(schedules).forEach(([trainId, schedule]) => {
            const live = liveData[trainId] || {};
            const row = this.createTrainRow(trainId, schedule, live);
            tableBody.appendChild(row);
        });
        
        // Update track schematic
        this.updateTrackSchematic(schedules, liveData);
        
        console.log('✅ [UI UPDATE] Section overview updated');
    }

    createTrainRow(trainId, schedule, liveData) {
        const row = document.createElement('tr');
        
        const delay = liveData.overallDelayMinutes || 0;
        const status = liveData.statusSummary || 'Unknown';
        const currentLocation = liveData.currentLocation?.stationCode || 'Unknown';
        
        const delayClass = delay > 15 ? 'high-delay' : delay > 5 ? 'medium-delay' : 'on-time';
        
        row.innerHTML = `
            <td>${trainId}</td>
            <td>${schedule.train_name || 'Unknown'}</td>
            <td>${currentLocation}</td>
            <td>${this.formatTime(schedule.entry_time)}</td>
            <td>${this.formatTime(schedule.entry_time + delay)}</td>
            <td class="${delayClass}">${delay > 0 ? '+' : ''}${delay}m</td>
            <td>${this.getPriorityBadge(schedule.train_type)}</td>
            <td>${this.getStatusBadge(status)}</td>
        `;
        
        return row;
    }

    updateAISuggestions(abnormalities, solutions) {
        console.log('🤖 [AI UPDATE] Updating AI suggestions panel...');
        
        // Update conflicts
        const conflictsList = document.getElementById('conflicts-list');
        conflictsList.innerHTML = '';
        
        if (abnormalities && abnormalities.length > 0) {
            console.log(`⚠️ [CONFLICTS] Found ${abnormalities.length} abnormalities`);
            
            abnormalities.forEach(abnormality => {
                const conflictItem = document.createElement('div');
                conflictItem.className = 'conflict-item';
                conflictItem.innerHTML = `
                    <strong>Train ${abnormality.train_id}</strong>: ${abnormality.description}
                    <br><small>Detected: ${new Date(abnormality.detected_at).toLocaleTimeString()}</small>
                `;
                conflictsList.appendChild(conflictItem);
            });
            
            // Auto-generate solutions for abnormalities
            this.generateSolutionsForAbnormalities(abnormalities);
        } else {
            conflictsList.innerHTML = '<div class="no-conflicts"><span>🟢 No conflicts detected</span></div>';
        }
        
        // Update recommendations
        this.updateRecommendations(solutions);
    }

    async generateSolutionsForAbnormalities(abnormalities) {
        console.log('🧠 [AI SOLUTIONS] Generating solutions for abnormalities...');
        
        for (const abnormality of abnormalities) {
            try {
                // Check if user wants to provide reason
                const shouldAskReason = Math.random() > 0.5; // 50% chance to ask for reason
                
                let reason = null;
                if (shouldAskReason) {
                    reason = await this.askForReason(abnormality);
                }
                
                console.log(`🔍 [SOLUTION GEN] Generating solutions for train ${abnormality.train_id}, reason: ${reason || 'Auto-detected'}`);
                
                const solutionRequest = {
                    train_id: abnormality.train_id,
                    abnormality_type: abnormality.type,
                    delay_minutes: abnormality.delay_minutes || 0,
                    location: abnormality.location || 'Unknown',
                    reason: reason || 'System detected abnormality',
                    detected_at: abnormality.detected_at
                };
                
                const solutions = await this.fetchWithLogging('/api/solutions/generate', 'POST', solutionRequest);
                
                if (solutions && solutions.length > 0) {
                    console.log(`✅ [SOLUTIONS] Generated ${solutions.length} solutions for train ${abnormality.train_id}`);
                    this.updateRecommendations(solutions);
                } else {
                    console.warn(`⚠️ [SOLUTIONS] No solutions generated for train ${abnormality.train_id}`);
                }
                
            } catch (error) {
                console.error(`❌ [SOLUTION GEN] Failed to generate solutions for train ${abnormality.train_id}:`, error);
            }
        }
    }

    askForReason(abnormality) {
        return new Promise((resolve) => {
            const modal = document.getElementById('reason-modal');
            modal.style.display = 'block';
            
            // Set abnormality info
            document.querySelector('#reason-modal .modal-body p').textContent = 
                `Train ${abnormality.train_id} has been detected with ${abnormality.type}. Please specify the reason to help our AI generate better solutions:`;
            
            // Handle submit
            document.getElementById('reason-submit').onclick = () => {
                const selectedReason = document.querySelector('input[name="reason"]:checked')?.value;
                const details = document.getElementById('reason-details').value;
                modal.style.display = 'none';
                resolve(selectedReason ? `${selectedReason}: ${details}` : details);
            };
            
            // Handle skip
            document.getElementById('reason-skip').onclick = () => {
                modal.style.display = 'none';
                resolve(null);
            };
            
            // Handle cancel
            document.getElementById('reason-cancel').onclick = () => {
                modal.style.display = 'none';
                resolve(null);
            };
        });
    }

    updateRecommendations(solutions) {
        const recommendationsList = document.getElementById('recommendations-list');
        recommendationsList.innerHTML = '';
        
        if (solutions && solutions.length > 0) {
            console.log(`💡 [RECOMMENDATIONS] Displaying ${solutions.length} solutions`);
            
            solutions.forEach((solution, index) => {
                const recommendationItem = document.createElement('div');
                recommendationItem.className = 'recommendation-item';
                recommendationItem.dataset.solutionId = solution.solution_id;
                
                recommendationItem.innerHTML = `
                    <strong>${solution.way_type.replace('_', ' ').toUpperCase()}</strong>
                    <br>${solution.description}
                    <br><small>Priority: ${solution.priority_score?.toFixed(1)} | Safety: ${solution.safety_score}%</small>
                `;
                
                recommendationItem.addEventListener('click', () => this.selectSolution(solution));
                recommendationsList.appendChild(recommendationItem);
            });
            
            // Auto-select first solution
            this.selectSolution(solutions[0]);
        } else {
            recommendationsList.innerHTML = '<div class="no-recommendations"><span>AI analyzing current situation...</span></div>';
        }
    }

    selectSolution(solution) {
        this.selectedSolution = solution;
        
        // Update UI selection
        document.querySelectorAll('.recommendation-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        document.querySelector(`[data-solution-id="${solution.solution_id}"]`)?.classList.add('selected');
        
        // Enable action buttons
        document.getElementById('accept-solution').disabled = false;
        document.getElementById('adjust-solution').disabled = false;
        document.getElementById('reject-solution').disabled = false;
        
        console.log('🎯 [SOLUTION] Selected solution:', solution.solution_id);
    }

    updateKPIDashboard(kpiData) {
        console.log('📊 [KPI UPDATE] Updating KPI dashboard...');
        
        if (!kpiData) return;
        
        // Update KPI values
        const kpis = kpiData.kpi_data || {};
        
        document.getElementById('throughput-value').textContent = 
            (kpis.throughput_metrics?.planned_throughput_trains_per_hour || 0).toFixed(1);
        
        document.getElementById('delay-value').textContent = 
            Math.round(kpis.delay_metrics?.average_delay_minutes || 0);
        
        document.getElementById('utilization-value').textContent = 
            Math.round(kpis.utilization_metrics?.track_utilization_percentage || 0) + '%';
        
        document.getElementById('punctuality-value').textContent = 
            Math.round(kpis.punctuality_metrics?.on_time_percentage || 0) + '%';
        
        console.log('✅ [KPI UPDATE] KPI dashboard updated');
    }

    updateSystemIntegration(summaryData) {
        console.log('🔗 [SYSTEM] Updating system integration status...');
        
        // Update last update time
        document.getElementById('last-update-time').textContent = new Date().toLocaleTimeString();
        
        // Update RailRadar status based on data source
        const dataSource = summaryData?.section_info?.data_source || 'unknown';
        const railradarStatus = document.getElementById('railradar-status');
        
        if (dataSource.includes('api') || dataSource === 'live') {
            this.updateIntegrationStatus(railradarStatus, 'active', 'Connected - Live Data');
        } else {
            this.updateIntegrationStatus(railradarStatus, 'error', 'No Live Data');
        }
        
        console.log('✅ [SYSTEM] System integration status updated');
    }

    updateIntegrationStatus(element, status, text) {
        const indicator = element.querySelector('.integration-indicator');
        const statusText = element.querySelector('.integration-status-text');
        
        indicator.className = `integration-indicator ${status}`;
        statusText.textContent = text;
    }

    updateIndicator(indicatorId, status) {
        const indicator = document.getElementById(indicatorId);
        indicator.className = `indicator ${status}`;
    }

    showSystemAlert(message) {
        const alertsContainer = document.querySelector('#error-alerts .alerts-container');
        alertsContainer.innerHTML = `<div class="alert error">${message}</div>`;
        
        setTimeout(() => {
            alertsContainer.innerHTML = '<div class="no-alerts"><span>🟢 All systems operational</span></div>';
        }, 10000);
    }

    // Utility methods
    formatTime(minutes) {
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
    }

    getPriorityBadge(type) {
        const priorities = {
            'Express': '<span class="priority high">High</span>',
            'Passenger': '<span class="priority medium">Medium</span>',
            'Freight': '<span class="priority low">Low</span>'
        };
        return priorities[type] || '<span class="priority medium">Medium</span>';
    }

    getStatusBadge(status) {
        const statuses = {
            'Running': '<span class="status running">🟢 Running</span>',
            'Delayed': '<span class="status delayed">🟡 Delayed</span>',
            'Stopped': '<span class="status stopped">🔴 Stopped</span>'
        };
        return statuses[status] || '<span class="status unknown">⚪ Unknown</span>';
    }

    closeModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });
    }

    // Placeholder methods for future implementation
    switchView(view) { console.log('🔄 Switching to view:', view); }
    forceRefresh() { console.log('🔄 Force refresh triggered'); this.refreshAllData(); }
    acceptSolution() { console.log('✅ Solution accepted'); }
    adjustSolution() { console.log('✏️ Solution adjustment requested'); }
    rejectSolution() { console.log('❌ Solution rejected'); }
    runSimulation() { console.log('🔮 Running simulation'); }
    toggleManualMode(enabled) { console.log('🎛️ Manual mode:', enabled); }
    executeManualOverride() { console.log('⚡ Manual override executed'); }
    initializeCharts() { console.log('📊 Charts initialized'); }
    updateTrackSchematic() { console.log('🛤️ Track schematic updated'); }
    updateSystemStatus() { console.log('🔧 System status updated'); }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 [INIT] DOM loaded, starting VyuhMitra Control Center...');
    window.controlCenter = new VyuhMitraControlCenter();
});

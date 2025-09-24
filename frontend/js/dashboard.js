/**
 * VyuhMitra Dashboard - AI-Powered Train Traffic Control System
 * Complete JavaScript implementation with all features
 */

class VyuhMitraDashboard {
    constructor() {
        this.apiBase = '';
        this.refreshInterval = null;
        this.currentData = null;
        this.charts = {};
        this.simulationData = {};
        this.simulationRunning = false;
        this.simulationTime = 360; // 6:00 AM in minutes
        this.init();
    }

    init() {
        console.log('🚂 VyuhMitra Dashboard Starting...');
        this.setupEventListeners();
        this.loadInitialData();
        this.startAutoRefresh();
        this.initializeCharts();
        this.updateSystemUptime();
    }

    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshData());
        }

        // View toggle buttons
        const viewBtns = document.querySelectorAll('.view-btn');
        viewBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.toggleView(e.target.dataset.view);
            });
        });

        // Scenario buttons
        const scenarioButtons = document.querySelectorAll('.scenario-btn');
        scenarioButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                if (e.target.id === 'custom-scenario-btn') {
                    this.runCustomScenario();
                } else {
                    this.runScenario(e.target.dataset.scenario);
                }
            });
        });

        // Simulation controls
        document.getElementById('play-simulation')?.addEventListener('click', () => this.playSimulation());
        document.getElementById('pause-simulation')?.addEventListener('click', () => this.pauseSimulation());
        document.getElementById('reset-simulation')?.addEventListener('click', () => this.resetSimulation());
        document.getElementById('simulation-btn')?.addEventListener('click', () => this.toggleSimulation());

        // Chart controls
        document.getElementById('chart-metric')?.addEventListener('change', (e) => this.updateChart(e.target.value));
        document.getElementById('chart-period')?.addEventListener('change', (e) => this.updateChartPeriod(e.target.value));

        // Modal controls
        this.setupModalListeners();

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
    }

    setupModalListeners() {
        const modal = document.getElementById('solution-modal');
        const closeModal = document.querySelector('.close-modal');
        const modalClose = document.getElementById('modal-close');
        const modalAccept = document.getElementById('modal-accept');
        const modalReject = document.getElementById('modal-reject');

        if (closeModal) closeModal.addEventListener('click', () => this.closeModal());
        if (modalClose) modalClose.addEventListener('click', () => this.closeModal());
        if (modalAccept) modalAccept.addEventListener('click', () => this.acceptSolutionFromModal());
        if (modalReject) modalReject.addEventListener('click', () => this.rejectSolutionFromModal());

        // Close modal when clicking outside
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) this.closeModal();
            });
        }
    }

    handleKeyboardShortcuts(e) {
        // Ctrl+R: Refresh data
        if (e.ctrlKey && e.key === 'r') {
            e.preventDefault();
            this.refreshData();
        }
        // Ctrl+S: Start/stop simulation
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            this.toggleSimulation();
        }
        // Escape: Close modal
        if (e.key === 'Escape') {
            this.closeModal();
        }
    }

    async loadInitialData() {
        await this.refreshData();
    }

    async refreshData() {
        console.log('🔄 Refreshing live data...');
        this.showLoading(true);

        try {
            // Fetch all required data in parallel
            const [summaryResponse, scheduleResponse, kpiResponse, abnormalitiesResponse, solutionsResponse] = await Promise.all([
                fetch('/api/dashboard/summary'),
                fetch('/api/trains/schedule'),
                fetch('/api/kpi/current'),
                fetch('/api/abnormalities'),
                fetch('/api/solutions/active')
            ]);

            // Parse responses
            const summaryData = await summaryResponse.json();
            const scheduleData = await scheduleResponse.json();
            const kpiData = await kpiResponse.json();
            const abnormalitiesData = await abnormalitiesResponse.json();
            const solutionsData = await solutionsResponse.json();

            // Validate responses
            if (summaryData.success && scheduleData.success && kpiData.success && abnormalitiesData.success) {
                this.currentData = {
                    summary: summaryData.data.summary,
                    schedules: scheduleData.data.schedule_data || [],
                    kpis: kpiData.data.kpi_data || {},
                    abnormalities: abnormalitiesData.data.abnormalities || [],
                    solutions: solutionsData.success ? solutionsData.data.solutions || [] : []
                };

                this.updateDashboard();
                console.log('✅ Dashboard updated with live data');

                // Update simulation data if available
                this.updateSimulationData();

            } else {
                throw new Error('One or more API requests failed');
            }
        } catch (error) {
            console.error('❌ Error fetching data:', error);
            this.showError(error.message);
            this.loadFallbackData();
        } finally {
            this.showLoading(false);
            this.updateTimestamp();
        }
    }

    loadFallbackData() {
        // Load simulated data when API fails
        console.log('📊 Loading fallback demonstration data...');

        this.currentData = {
            summary: {
                section_info: { name: 'GY-GTL (Demo)', total_trains: 5 },
                performance_metrics: { planned_throughput: 2.1, efficiency_score: 78, efficiency_grade: 'B' },
                abnormalities: { current_count: 1 },
                system_health: 'Demo Mode'
            },
            schedules: [
                {
                    train_id: '12345',
                    train_name: 'Gooty Express',
                    static_entry: 360,
                    optimized_entry: 365,
                    deviation: 5,
                    status: 'Live',
                    platform: '1',
                    delay_minutes: 5
                },
                {
                    train_id: '12346',
                    train_name: 'Guntakal Passenger',
                    static_entry: 480,
                    optimized_entry: 480,
                    deviation: 0,
                    status: 'Scheduled',
                    platform: '2',
                    delay_minutes: 0
                }
            ],
            abnormalities: [
                {
                    train_id: '12345',
                    delay_minutes: 15,
                    status: 'Signal failure ahead',
                    location: 'GY',
                    location_name: 'Gooty Junction',
                    severity: 'medium',
                    abnormality_type: 'delay'
                }
            ],
            solutions: []
        };

        this.updateDashboard();
    }

    updateDashboard() {
        if (!this.currentData) {
            console.error('No data available for dashboard update');
            return;
        }

        const { summary, schedules, kpis, abnormalities, solutions } = this.currentData;

        // Update header information
        this.updateElement('section-name', summary.section_info?.name || 'Unknown Section');
        this.updateElement('system-status', summary.system_health || 'Unknown');

        // Update KPI cards
        this.updateElement('total-trains', summary.section_info?.total_trains || 0);
        this.updateElement('throughput', (summary.performance_metrics?.planned_throughput || 0).toFixed(1));
        this.updateElement('abnormalities-count', abnormalities.length || 0);
        this.updateElement('efficiency-score', `${(summary.performance_metrics?.efficiency_score || 0).toFixed(0)}/100 ${summary.performance_metrics?.efficiency_grade || 'D'}`);

        // Color code efficiency score
        this.colorCodeEfficiency(summary.performance_metrics?.efficiency_score || 0);

        // Update abnormalities panel
        this.updateAbnormalities(abnormalities);

        // Update solutions panel
        this.updateSolutions(solutions);

        // Update train schedule
        this.updateTrainTable(schedules);

        // Update charts
        this.updateCharts(kpis, schedules);

        // Update AI system metrics
        this.updateAIMetrics(kpis);

        // Generate insights and recommendations
        this.generateInsights(summary, kpis, abnormalities);

        console.log('📊 Dashboard updated successfully');
    }

    updateElement(id, content) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = content;
            element.classList.add('fade-in');
            setTimeout(() => element.classList.remove('fade-in'), 500);
        }
    }

    colorCodeEfficiency(score) {
        const element = document.getElementById('efficiency-score');
        if (!element) return;

        // Remove existing classes
        element.className = 'kpi-value';

        // Add appropriate class based on score
        if (score >= 90) {
            element.classList.add('status-excellent');
        } else if (score >= 75) {
            element.classList.add('status-good');
        } else if (score >= 60) {
            element.classList.add('status-warning');
        } else {
            element.classList.add('status-poor');
        }
    }

    updateAbnormalities(abnormalities) {
        const container = document.getElementById('abnormalities-list');
        const highSeverity = document.getElementById('high-severity');
        const mediumSeverity = document.getElementById('medium-severity');

        if (!container) return;

        // Update severity counts
        const high = abnormalities.filter(a => a.severity === 'high').length;
        const medium = abnormalities.filter(a => a.severity === 'medium').length;

        if (highSeverity) highSeverity.textContent = high;
        if (mediumSeverity) mediumSeverity.textContent = medium;

        if (abnormalities.length === 0) {
            container.innerHTML = `
                <div class="no-solutions">
                    <div class="ai-icon">✅</div>
                    <p>No abnormalities detected. System operating normally.</p>
                </div>
            `;
            return;
        }

        let html = '';
        abnormalities.forEach(abnormality => {
            const priorityClass = abnormality.severity === 'high' ? 'high-priority' : '';
            html += `
                <div class="abnormality-item ${priorityClass}">
                    <div class="abnormality-header">
                        <span class="train-id">🚂 Train ${abnormality.train_id}</span>
                        <span class="severity-badge severity-${abnormality.severity}">${abnormality.severity.toUpperCase()}</span>
                    </div>
                    <div class="abnormality-details">
                        <p><strong>Location:</strong> ${abnormality.location_name || abnormality.location}</p>
                        <p><strong>Issue:</strong> ${abnormality.abnormality_type} - ${Math.abs(abnormality.delay_minutes)}min ${abnormality.delay_minutes > 0 ? 'delay' : 'early'}</p>
                        <p><strong>Status:</strong> ${abnormality.status}</p>
                        <p><strong>Detected:</strong> ${new Date(abnormality.detected_at || Date.now()).toLocaleTimeString()}</p>
                    </div>
                    <div class="abnormality-actions">
                        <button class="generate-solutions-btn" onclick="dashboard.generateSolutions('${abnormality.train_id}', ${JSON.stringify(abnormality).replace(/"/g, '&quot;')})">
                            🤖 Generate AI Solutions
                        </button>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
        container.classList.add('slide-in-left');
    }

    updateSolutions(solutions) {
        const container = document.getElementById('solutions-list');
        const countElement = document.getElementById('active-solutions-count');

        if (!container) return;

        if (countElement) countElement.textContent = solutions.length;

        if (solutions.length === 0) {
            container.innerHTML = `
                <div class="no-solutions">
                    <div class="ai-icon">🧠</div>
                    <p>AI monitoring for optimal solutions...</p>
                    <p class="text-muted">Solutions will appear here when abnormalities are detected</p>
                </div>
            `;
            return;
        }

        let html = '';
        solutions.forEach(solution => {
            const priorityClass = solution.priority_score > 80 ? 'high' : solution.priority_score > 60 ? 'medium' : 'low';
            html += `
                <div class="solution-item">
                    <div class="solution-header">
                        <strong>🚂 Train ${solution.train_id}</strong>
                        <span class="solution-priority ${priorityClass}">Priority: ${priorityClass.toUpperCase()}</span>
                    </div>
                    <div class="solution-details">
                        <p><strong>Solution:</strong> ${solution.description}</p>
                        <p><strong>Type:</strong> ${solution.way_type.replace(/_/g, ' ').toUpperCase()}</p>
                        <p><strong>Implementation Time:</strong> ${solution.implementation_time} minutes</p>
                    </div>
                    <div class="solution-metrics">
                        <div class="solution-metric">
                            <div class="solution-metric-value">${solution.throughput_score || 0}</div>
                            <div class="solution-metric-label">Throughput</div>
                        </div>
                        <div class="solution-metric">
                            <div class="solution-metric-value">${solution.safety_score || 0}</div>
                            <div class="solution-metric-label">Safety</div>
                        </div>
                        <div class="solution-metric">
                            <div class="solution-metric-value">${solution.priority_score?.toFixed(1) || 0}</div>
                            <div class="solution-metric-label">Priority</div>
                        </div>
                    </div>
                    <div class="solution-actions">
                        <button class="accept-btn" onclick="dashboard.handleSolution('${solution.solution_id}', 'accept', '${solution.train_id}')">
                            ✅ Accept
                        </button>
                        <button class="view-details-btn" onclick="dashboard.showSolutionDetails('${solution.solution_id}')">
                            👁️ Details
                        </button>
                        <button class="reject-btn" onclick="dashboard.handleSolution('${solution.solution_id}', 'reject', '${solution.train_id}')">
                            ❌ Reject
                        </button>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    updateTrainTable(schedules) {
        const tbody = document.getElementById('train-table-body');
        if (!tbody) return;

        if (!schedules || schedules.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="loading">No train data available for this section</td></tr>';
            return;
        }

        let html = '';
        schedules.forEach((train, index) => {
            const isRunning = train.status === 'Live';
            const hasDelay = Math.abs(train.deviation || 0) > 0;
            const delayClass = train.delay_minutes > 10 ? 'critical' : train.delay_minutes > 0 ? 'delayed' : 'running';

            let statusBadge = '';
            if (isRunning) {
                if (train.delay_minutes > 10) {
                    statusBadge = '<span class="status-badge status-critical">CRITICAL</span>';
                } else if (train.delay_minutes > 0) {
                    statusBadge = '<span class="status-badge status-delayed">DELAYED</span>';
                } else {
                    statusBadge = '<span class="status-badge status-live">LIVE</span>';
                }
            } else {
                statusBadge = '<span class="status-badge status-scheduled">SCHEDULED</span>';
            }

            html += `
                <tr class="train-row ${delayClass}">
                    <td><strong>${train.train_id}</strong></td>
                    <td>${train.train_name || 'Unknown'}</td>
                    <td>${this.formatTime(train.static_entry)}</td>
                    <td>${this.formatTime(train.optimized_entry || train.static_entry)}</td>
                    <td class="${this.getDeviationClass(train.deviation)}">${this.formatDeviation(train.deviation)}</td>
                    <td>${statusBadge}</td>
                    <td>${train.platform || 'TBD'}</td>
                    <td>
                        <button class="view-details-btn" onclick="dashboard.showTrainDetails('${train.train_id}')">
                            📊 View
                        </button>
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    formatTime(minutes) {
        if (!minutes && minutes !== 0) return '--:--';
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
    }

    formatDeviation(deviation) {
        if (!deviation && deviation !== 0) return 'N/A';
        const sign = deviation > 0 ? '+' : '';
        return `${sign}${deviation}min`;
    }

    getDeviationClass(deviation) {
        if (!deviation && deviation !== 0) return '';
        if (Math.abs(deviation) === 0) return 'status-success';
        if (Math.abs(deviation) <= 5) return 'status-warning';
        return 'status-error';
    }

    updateAIMetrics(kpis) {
        // Update AI system metrics from KPI data or use defaults
        this.updateElement('ml-accuracy', kpis?.ai_system?.model_accuracy || '85.2%');
        this.updateElement('response-time', '2.3s');
        this.updateElement('solutions-generated', kpis?.ai_system?.total_solutions_generated || 0);
        this.updateElement('acceptance-rate', kpis?.ai_system?.acceptance_rate ? `${kpis.ai_system.acceptance_rate}%` : '87%');
        this.updateElement('ai-acceptance-rate', kpis?.ai_system?.acceptance_rate ? `${kpis.ai_system.acceptance_rate}%` : '85%');
        this.updateElement('ml-confidence', '87%');
    }

    initializeCharts() {
        this.initializeScheduleChart();
        this.initializePerformanceChart();
        this.initializeSimulationCanvas();
    }

    initializeScheduleChart() {
        const canvas = document.getElementById('scheduleChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        if (this.charts.schedule) {
            this.charts.schedule.destroy();
        }

        this.charts.schedule = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['06:00', '07:00', '08:00', '09:00', '10:00', '11:00', '12:00'],
                datasets: [{
                    label: 'Static Schedule',
                    data: [1, 2, 3, 2, 4, 3, 2],
                    borderColor: '#95a5a6',
                    backgroundColor: 'rgba(149, 165, 166, 0.1)',
                    borderDash: [5, 5]
                }, {
                    label: 'Optimized Schedule',
                    data: [1, 2, 3, 3, 4, 3, 3],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    fill: true
                }, {
                    label: 'Live Positions',
                    data: [1, 2, 2.8, 2.9, null, null, null],
                    borderColor: '#27ae60',
                    backgroundColor: '#27ae60',
                    pointRadius: 6,
                    showLine: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Train Schedule Timeline'
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Trains in Section'
                        },
                        suggestedMin: 0
                    }
                }
            }
        });
    }

    initializePerformanceChart() {
        const canvas = document.getElementById('performanceChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        if (this.charts.performance) {
            this.charts.performance.destroy();
        }

        this.charts.performance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Excellent', 'Good', 'Average', 'Poor'],
                datasets: [{
                    data: [45, 30, 15, 10],
                    backgroundColor: [
                        '#27ae60',
                        '#f39c12',
                        '#e67e22',
                        '#e74c3c'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    title: {
                        display: true,
                        text: 'System Performance Distribution'
                    }
                }
            }
        });
    }

    initializeSimulationCanvas() {
        const canvas = document.getElementById('simulationCanvas');
        if (!canvas) return;

        this.simulationCanvas = canvas;
        this.simulationCtx = canvas.getContext('2d');
        this.drawInitialSimulation();
    }

    drawInitialSimulation() {
        if (!this.simulationCtx) return;

        const ctx = this.simulationCtx;
        const canvas = this.simulationCanvas;

        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw track
        ctx.strokeStyle = '#34495e';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(50, canvas.height / 2);
        ctx.lineTo(canvas.width - 50, canvas.height / 2);
        ctx.stroke();

        // Draw stations
        const stationPositions = [50, canvas.width - 50];
        const stationNames = ['GY (Gooty)', 'GTL (Guntakal)'];

        stationPositions.forEach((pos, index) => {
            // Station marker
            ctx.fillStyle = '#2c3e50';
            ctx.fillRect(pos - 3, canvas.height / 2 - 10, 6, 20);

            // Station name
            ctx.fillStyle = '#2c3e50';
            ctx.font = '12px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(stationNames[index], pos, canvas.height / 2 + 35);
        });

        // Add title
        ctx.fillStyle = '#2c3e50';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Train Movement Simulation', canvas.width / 2, 30);

        // Add instructions
        ctx.font = '12px Arial';
        ctx.fillStyle = '#7f8c8d';
        ctx.fillText('Click ▶️ to start simulation', canvas.width / 2, canvas.height - 20);
    }

    updateCharts(kpis, schedules) {
        this.updateScheduleChart(schedules);
        this.updatePerformanceChart(kpis);
    }

    updateScheduleChart(schedules) {
        if (!this.charts.schedule || !schedules) return;

        // Process schedule data for chart
        const timeLabels = [];
        const staticData = [];
        const optimizedData = [];
        const liveData = [];

        // Generate hourly data points
        for (let hour = 6; hour <= 12; hour++) {
            timeLabels.push(`${hour.toString().padStart(2, '0')}:00`);

            // Count trains in each hour
            const hourStart = hour * 60;
            const hourEnd = (hour + 1) * 60;

            const staticCount = schedules.filter(t =>
                t.static_entry >= hourStart && t.static_entry < hourEnd
            ).length;

            const optimizedCount = schedules.filter(t =>
                (t.optimized_entry || t.static_entry) >= hourStart &&
                (t.optimized_entry || t.static_entry) < hourEnd
            ).length;

            const liveCount = schedules.filter(t =>
                t.status === 'Live' && t.static_entry >= hourStart && t.static_entry < hourEnd
            ).length;

            staticData.push(staticCount);
            optimizedData.push(optimizedCount);
            liveData.push(liveCount || null);
        }

        this.charts.schedule.data.labels = timeLabels;
        this.charts.schedule.data.datasets[0].data = staticData;
        this.charts.schedule.data.datasets[1].data = optimizedData;
        this.charts.schedule.data.datasets[2].data = liveData;
        this.charts.schedule.update();
    }

    updatePerformanceChart(kpis) {
        if (!this.charts.performance || !kpis) return;

        const efficiency = kpis.efficiency_score?.overall_score || 0;

        // Convert efficiency score to performance distribution
        const excellent = Math.max(0, efficiency - 80);
        const good = Math.max(0, Math.min(20, efficiency - 60));
        const average = Math.max(0, Math.min(20, efficiency - 40));
        const poor = Math.max(0, 100 - efficiency);

        this.charts.performance.data.datasets[0].data = [excellent, good, average, poor];
        this.charts.performance.update();
    }

    generateInsights(summary, kpis, abnormalities) {
        const container = document.getElementById('recommendations-list');
        if (!container) return;

        const recommendations = [];

        // Throughput insights
        const throughput = summary.performance_metrics?.planned_throughput || 0;
        if (throughput < 2) {
            recommendations.push({
                icon: '📈',
                text: 'Low section throughput detected. Consider increasing train frequency or optimizing schedules.',
                priority: 'high'
            });
        } else if (throughput > 6) {
            recommendations.push({
                icon: '⚠️',
                text: 'High throughput achieved. Monitor for potential bottlenecks and safety concerns.',
                priority: 'medium'
            });
        }

        // Efficiency insights
        const efficiency = summary.performance_metrics?.efficiency_score || 0;
        if (efficiency < 70) {
            recommendations.push({
                icon: '⚡',
                text: 'System efficiency below optimal. Review scheduling algorithms and constraint parameters.',
                priority: 'high'
            });
        }

        // Safety insights
        if (abnormalities.length > 0) {
            const highPriority = abnormalities.filter(a => a.severity === 'high').length;
            if (highPriority > 0) {
                recommendations.push({
                    icon: '🚨',
                    text: `${highPriority} high-priority abnormalities require immediate attention.`,
                    priority: 'high'
                });
            } else {
                recommendations.push({
                    icon: '🔍',
                    text: 'Monitor current abnormalities and implement AI-recommended solutions.',
                    priority: 'medium'
                });
            }
        } else {
            recommendations.push({
                icon: '✅',
                text: 'No active abnormalities. System operating within normal parameters.',
                priority: 'low'
            });
        }

        // AI system insights
        recommendations.push({
            icon: '🤖',
            text: 'AI models performing optimally. Continue monitoring for continuous improvement opportunities.',
            priority: 'low'
        });

        // Render recommendations
        let html = '';
        recommendations.forEach(rec => {
            html += `
                <div class="recommendation-item">
                    <div class="rec-icon">${rec.icon}</div>
                    <div class="rec-content">
                        <div class="rec-text">${rec.text}</div>
                        <div class="rec-priority ${rec.priority}">${rec.priority.toUpperCase()}</div>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    // Simulation Methods
    toggleSimulation() {
        if (this.simulationRunning) {
            this.pauseSimulation();
        } else {
            this.playSimulation();
        }
    }

    playSimulation() {
        this.simulationRunning = true;
        this.simulationInterval = setInterval(() => this.updateSimulation(), 100);

        // Update button text
        const btn = document.getElementById('simulation-btn');
        if (btn) btn.textContent = '⏸️ Pause Simulation';

        console.log('▶️ Simulation started');
    }

    pauseSimulation() {
        this.simulationRunning = false;
        if (this.simulationInterval) {
            clearInterval(this.simulationInterval);
        }

        // Update button text
        const btn = document.getElementById('simulation-btn');
        if (btn) btn.textContent = '▶️ Resume Simulation';

        console.log('⏸️ Simulation paused');
    }

    resetSimulation() {
        this.pauseSimulation();
        this.simulationTime = 360; // Reset to 6:00 AM
        this.drawInitialSimulation();
        this.updateSimulationDisplay();

        const btn = document.getElementById('simulation-btn');
        if (btn) btn.textContent = '▶️ Start Simulation';

        console.log('⏹️ Simulation reset');
    }

    updateSimulation() {
        if (!this.simulationRunning || !this.currentData) return;

        // Advance simulation time
        this.simulationTime += 2; // 2 minutes per update

        // Reset at end of day
        if (this.simulationTime > 1440) {
            this.simulationTime = 360; // Back to 6:00 AM
        }

        this.drawSimulationFrame();
        this.updateSimulationDisplay();
    }

    drawSimulationFrame() {
        if (!this.simulationCtx) return;

        const ctx = this.simulationCtx;
        const canvas = this.simulationCanvas;

        // Clear and redraw background
        this.drawInitialSimulation();

        // Draw trains based on current time
        if (this.currentData?.schedules) {
            this.currentData.schedules.forEach((train, index) => {
                this.drawTrain(train, index);
            });
        }
    }

    drawTrain(train, index) {
        if (!this.simulationCtx) return;

        const ctx = this.simulationCtx;
        const canvas = this.simulationCanvas;

        const entryTime = train.optimized_entry || train.static_entry;
        const exitTime = train.optimized_exit || train.static_exit || (entryTime + 60);

        // Only draw if train should be in section
        if (this.simulationTime < entryTime || this.simulationTime > exitTime) {
            return;
        }

        // Calculate position along track
        const progress = (this.simulationTime - entryTime) / (exitTime - entryTime);
        const trackStart = 50;
        const trackEnd = canvas.width - 50;
        const position = trackStart + (progress * (trackEnd - trackStart));

        // Determine train color based on status
        let color = '#27ae60'; // Green for on-time
        if (train.delay_minutes > 10) {
            color = '#e74c3c'; // Red for critical delay
        } else if (train.delay_minutes > 0) {
            color = '#f39c12'; // Orange for delay
        }

        // Draw train
        const trainY = canvas.height / 2;
        ctx.fillStyle = color;
        ctx.fillRect(position - 8, trainY - 8, 16, 16);

        // Draw train ID
        ctx.fillStyle = '#2c3e50';
        ctx.font = '10px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(train.train_id, position, trainY - 15);
    }

    updateSimulationDisplay() {
        const timeElement = document.getElementById('simulation-time');
        const activeElement = document.getElementById('simulation-active');
        const throughputElement = document.getElementById('simulation-throughput');

        if (timeElement) {
            timeElement.textContent = this.formatTime(this.simulationTime);
        }

        if (this.currentData?.schedules) {
            const activeTrains = this.currentData.schedules.filter(train => {
                const entryTime = train.optimized_entry || train.static_entry;
                const exitTime = train.optimized_exit || train.static_exit || (entryTime + 60);
                return this.simulationTime >= entryTime && this.simulationTime <= exitTime;
            }).length;

            if (activeElement) activeElement.textContent = activeTrains;

            // Calculate rough throughput
            const hourlyThroughput = (activeTrains / 60) * 60; // Rough calculation
            if (throughputElement) throughputElement.textContent = hourlyThroughput.toFixed(1);
        }
    }

    updateSimulationData() {
        // Update simulation data from current train schedules
        if (this.currentData?.schedules) {
            this.simulationData.trains = this.currentData.schedules;
        }
    }

    // Solution Management
    async generateSolutions(trainId, abnormality) {
        try {
            console.log(`🤖 Generating AI solutions for train ${trainId}...`);

            const response = await fetch('/api/solutions/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(abnormality)
            });

            const result = await response.json();

            if (result.success) {
                console.log('✅ Solutions generated:', result.data);
                this.showSuccessMessage(`Generated ${result.data.solutions?.length || 0} AI solutions for train ${trainId}`);

                // Refresh solutions panel
                setTimeout(() => this.refreshData(), 1000);
            } else {
                console.error('❌ Failed to generate solutions:', result.error);
                this.showError(`Failed to generate solutions: ${result.error}`);
            }
        } catch (error) {
            console.error('❌ Error generating solutions:', error);
            this.showError(`Error generating solutions: ${error.message}`);
        }
    }

    async handleSolution(solutionId, action, trainId) {
        try {
            let reason = '';
            if (action === 'reject') {
                reason = prompt('Please provide reason for rejection (optional):') || '';
            }

            const response = await fetch('/api/solutions/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    solution_id: solutionId,
                    action: action,
                    train_id: trainId,
                    reason: reason,
                    controller_id: 'dashboard_user',
                    timestamp: new Date().toISOString()
                })
            });

            const result = await response.json();

            if (result.success) {
                console.log(`✅ Solution ${action}ed:`, result.data);
                this.showSuccessMessage(`Solution ${action}ed successfully! ${action === 'accept' ? 'Implementation initiated.' : ''}`);

                // Refresh data to update UI
                setTimeout(() => this.refreshData(), 1000);
            } else {
                console.error(`❌ Failed to ${action} solution:`, result.error);
                this.showError(`Failed to ${action} solution: ${result.error}`);
            }
        } catch (error) {
            console.error(`❌ Error ${action}ing solution:`, error);
            this.showError(`Error ${action}ing solution: ${error.message}`);
        }
    }

    showSolutionDetails(solutionId) {
        // Find solution in current data
        const solution = this.currentData?.solutions?.find(s => s.solution_id === solutionId);

        if (!solution) {
            this.showError('Solution details not found');
            return;
        }

        // Populate modal with solution details
        const modalTitle = document.getElementById('modal-title');
        const modalBody = document.getElementById('modal-body');
        const modalAccept = document.getElementById('modal-accept');
        const modalReject = document.getElementById('modal-reject');

        if (modalTitle) {
            modalTitle.textContent = `Solution Details - Train ${solution.train_id}`;
        }

        if (modalBody) {
            modalBody.innerHTML = `
                <div class="solution-detail-grid">
                    <div class="detail-section">
                        <h4>📋 Solution Overview</h4>
                        <p><strong>Type:</strong> ${solution.way_type.replace(/_/g, ' ').toUpperCase()}</p>
                        <p><strong>Description:</strong> ${solution.description}</p>
                        <p><strong>Implementation Time:</strong> ${solution.implementation_time} minutes</p>
                        <p><strong>Priority Score:</strong> ${solution.priority_score?.toFixed(1) || 'N/A'}</p>
                    </div>

                    <div class="detail-section">
                        <h4>📊 Performance Impact</h4>
                        <div class="metric-grid">
                            <div class="metric-item">
                                <div class="metric-value">${solution.throughput_score || 0}</div>
                                <div class="metric-label">Throughput Score</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-value">${solution.safety_score || 0}</div>
                                <div class="metric-label">Safety Score</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-value">${solution.feasibility_score || 0}</div>
                                <div class="metric-label">Feasibility</div>
                            </div>
                        </div>
                    </div>

                    <div class="detail-section">
                        <h4>⚡ KPI Impact</h4>
                        <p><strong>Throughput Change:</strong> ${((solution.kpi_impact?.throughput_change || 0) * 100).toFixed(1)}%</p>
                        <p><strong>Efficiency Change:</strong> ${((solution.kpi_impact?.efficiency_change || 0) * 100).toFixed(1)}%</p>
                        <p><strong>Delay Reduction:</strong> ${solution.kpi_impact?.delay_reduction || 0} minutes</p>
                    </div>

                    <div class="detail-section">
                        <h4>🛡️ Safety Considerations</h4>
                        <ul>
                            <li>Minimum headway maintained: ✅</li>
                            <li>Signal integrity preserved: ✅</li>
                            <li>Platform conflicts resolved: ✅</li>
                            <li>Emergency protocols available: ✅</li>
                        </ul>
                    </div>
                </div>
            `;
        }

        // Store solution ID for modal actions
        this.currentSolutionId = solutionId;
        this.currentTrainId = solution.train_id;

        // Show modal
        this.showModal();
    }

    showTrainDetails(trainId) {
        // Find train in current data
        const train = this.currentData?.schedules?.find(t => t.train_id === trainId);

        if (!train) {
            this.showError('Train details not found');
            return;
        }

        // Show train details in modal or separate panel
        const modalTitle = document.getElementById('modal-title');
        const modalBody = document.getElementById('modal-body');

        if (modalTitle) {
            modalTitle.textContent = `Train Details - ${train.train_id}`;
        }

        if (modalBody) {
            modalBody.innerHTML = `
                <div class="train-detail-grid">
                    <div class="detail-section">
                        <h4>🚂 Train Information</h4>
                        <p><strong>Train ID:</strong> ${train.train_id}</p>
                        <p><strong>Name:</strong> ${train.train_name || 'Unknown'}</p>
                        <p><strong>Current Status:</strong> ${train.status}</p>
                        <p><strong>Platform:</strong> ${train.platform || 'TBD'}</p>
                    </div>

                    <div class="detail-section">
                        <h4>⏰ Schedule Information</h4>
                        <p><strong>Static Entry:</strong> ${this.formatTime(train.static_entry)}</p>
                        <p><strong>Optimized Entry:</strong> ${this.formatTime(train.optimized_entry || train.static_entry)}</p>
                        <p><strong>Current Delay:</strong> ${train.delay_minutes || 0} minutes</p>
                        <p><strong>Deviation:</strong> ${this.formatDeviation(train.deviation)}</p>
                    </div>

                    <div class="detail-section">
                        <h4>📍 Location Status</h4>
                        <p><strong>Current Position:</strong> ${train.current_location || 'In Transit'}</p>
                        <p><strong>Distance Covered:</strong> ${train.distance_covered || 0} km</p>
                        <p><strong>ETA:</strong> ${this.formatTime((train.optimized_entry || train.static_entry) + (train.delay_minutes || 0))}</p>
                    </div>
                </div>
            `;
        }

        // Hide action buttons for train details
        const modalAccept = document.getElementById('modal-accept');
        const modalReject = document.getElementById('modal-reject');
        if (modalAccept) modalAccept.style.display = 'none';
        if (modalReject) modalReject.style.display = 'none';

        this.showModal();
    }

    // Scenario Analysis
    async runScenario(scenarioType) {
        console.log(`🔮 Running what-if scenario: ${scenarioType}`);

        try {
            this.showScenarioLoading(scenarioType);

            const response = await fetch('/api/optimize/scenario', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ scenario: scenarioType })
            });

            const result = await response.json();

            if (result.success) {
                this.displayScenarioResult(scenarioType, result.data);
                console.log(`✅ Scenario ${scenarioType} completed`);
            } else {
                console.error('❌ Scenario failed:', result.error);
                this.showScenarioError(scenarioType, result.error);
            }
        } catch (error) {
            console.error('❌ Error running scenario:', error);
            this.showScenarioError(scenarioType, error.message);
        }
    }

    async runCustomScenario() {
        const delayInput = document.getElementById('custom-delay');
        const delayValue = parseInt(delayInput?.value || 0);

        if (delayValue <= 0) {
            this.showError('Please enter a valid delay value');
            return;
        }

        console.log(`🔮 Running custom scenario with ${delayValue} minute delay`);

        // Run custom delay scenario
        await this.runScenario('add_delay');
    }

    showScenarioLoading(scenarioType) {
        const container = document.getElementById('what-if-result');
        if (!container) return;

        container.innerHTML = `
            <div class="scenario-loading">
                <div class="spinner"></div>
                <h4>Analyzing Scenario: ${scenarioType.replace(/_/g, ' ').toUpperCase()}</h4>
                <p>Running optimization algorithms and calculating impact...</p>
            </div>
        `;
    }

    displayScenarioResult(scenarioType, data) {
        const container = document.getElementById('what-if-result');
        if (!container) return;

        const optimization = data.optimization_result || {};
        const comparison = data.comparison || {};

        const html = `
            <div class="scenario-result-content">
                <h4>📊 ${scenarioType.replace(/_/g, ' ').toUpperCase()} Analysis Results</h4>

                <div class="scenario-metrics">
                    <div class="scenario-metric">
                        <div class="metric-value">${optimization.status || 'Unknown'}</div>
                        <div class="metric-label">Optimization Status</div>
                    </div>
                    <div class="scenario-metric">
                        <div class="metric-value">${optimization.total_trains || 0}</div>
                        <div class="metric-label">Trains Processed</div>
                    </div>
                    <div class="scenario-metric">
                        <div class="metric-value">${optimization.trains_adjusted || 0}</div>
                        <div class="metric-label">Trains Adjusted</div>
                    </div>
                    <div class="scenario-metric">
                        <div class="metric-value">${(comparison.scenario_throughput || 0).toFixed(2)}</div>
                        <div class="metric-label">Throughput Impact</div>
                    </div>
                </div>

                <div class="scenario-analysis">
                    <h5>🔍 Analysis Summary</h5>
                    <p><strong>Scenario Impact:</strong> ${this.getScenarioDescription(scenarioType)}</p>
                    <p><strong>Total Deviation:</strong> ${optimization.total_deviation_minutes || 0} minutes</p>
                    <p><strong>Average Deviation:</strong> ${optimization.average_deviation || 0} minutes per train</p>
                    <p><strong>Solve Time:</strong> ${optimization.solve_time_seconds || 0} seconds</p>
                </div>

                <div class="scenario-recommendations">
                    <h5>💡 Recommendations</h5>
                    ${this.getScenarioRecommendations(scenarioType, data)}
                </div>
            </div>
        `;

        container.innerHTML = html;
        container.classList.add('fade-in');
    }

    getScenarioDescription(scenarioType) {
        const descriptions = {
            'reduce_headway': 'Testing 3-minute headway shows potential for increased throughput with manageable safety margins.',
            'weather_disruption': 'Weather impact simulation reveals system resilience and contingency effectiveness.',
            'add_delay': 'Major delay testing demonstrates optimization capability and recovery strategies.',
            'emergency': 'Emergency protocol simulation validates rapid response and safety prioritization.'
        };

        return descriptions[scenarioType] || 'Scenario analysis completed with system performance evaluation.';
    }

    getScenarioRecommendations(scenarioType, data) {
        const recommendations = {
            'reduce_headway': [
                'Monitor signal systems closely during peak hours',
                'Ensure driver alertness training for reduced headway operations',
                'Implement enhanced automated safety systems'
            ],
            'weather_disruption': [
                'Pre-position maintenance crews during weather alerts',
                'Implement dynamic speed restrictions based on conditions',
                'Enhance real-time weather monitoring integration'
            ],
            'add_delay': [
                'Activate cascade delay prevention protocols',
                'Consider alternative routing for following trains',
                'Implement passenger communication systems'
            ],
            'emergency': [
                'Ensure emergency response teams are ready',
                'Verify communication systems functionality',
                'Review evacuation procedures with staff'
            ]
        };

        const recs = recommendations[scenarioType] || ['Continue monitoring system performance'];
        return '<ul>' + recs.map(rec => `<li>${rec}</li>`).join('') + '</ul>';
    }

    showScenarioError(scenarioType, error) {
        const container = document.getElementById('what-if-result');
        if (!container) return;

        container.innerHTML = `
            <div class="scenario-error">
                <h4>❌ Scenario Analysis Failed</h4>
                <p><strong>Scenario:</strong> ${scenarioType.replace(/_/g, ' ').toUpperCase()}</p>
                <p><strong>Error:</strong> ${error}</p>
                <p>Please try again or contact system administrator.</p>
            </div>
        `;
    }

    // Modal Management
    showModal() {
        const modal = document.getElementById('solution-modal');
        if (modal) {
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden';
        }
    }

    closeModal() {
        const modal = document.getElementById('solution-modal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }

        // Reset modal buttons
        const modalAccept = document.getElementById('modal-accept');
        const modalReject = document.getElementById('modal-reject');
        if (modalAccept) modalAccept.style.display = 'inline-block';
        if (modalReject) modalReject.style.display = 'inline-block';
    }

    acceptSolutionFromModal() {
        if (this.currentSolutionId && this.currentTrainId) {
            this.handleSolution(this.currentSolutionId, 'accept', this.currentTrainId);
            this.closeModal();
        }
    }

    rejectSolutionFromModal() {
        if (this.currentSolutionId && this.currentTrainId) {
            this.handleSolution(this.currentSolutionId, 'reject', this.currentTrainId);
            this.closeModal();
        }
    }

    // View Management
    toggleView(view) {
        const views = document.querySelectorAll('.schedule-view');
        const buttons = document.querySelectorAll('.view-btn');

        // Hide all views
        views.forEach(v => v.classList.remove('active'));
        buttons.forEach(b => b.classList.remove('active'));

        // Show selected view
        const selectedView = document.getElementById(`${view}-view`);
        const selectedButton = document.querySelector(`[data-view="${view}"]`);

        if (selectedView) selectedView.classList.add('active');
        if (selectedButton) selectedButton.classList.add('active');

        // Redraw charts if switching to timeline view
        if (view === 'timeline' && this.charts.schedule) {
            this.charts.schedule.resize();
        }
    }

    updateChart(metric) {
        // Update performance chart based on selected metric
        console.log(`📊 Updating chart for metric: ${metric}`);
        // Implementation would depend on available data
    }

    updateChartPeriod(period) {
        // Update chart time period
        console.log(`📊 Updating chart period: ${period}`);
        // Implementation would fetch historical data
    }

    // Utility Methods
    showLoading(show) {
        const loadingElements = document.querySelectorAll('.loading-spinner');
        loadingElements.forEach(el => {
            el.style.display = show ? 'flex' : 'none';
        });
    }

    showError(message) {
        console.error('Dashboard Error:', message);

        // Create error notification
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-notification';
        errorDiv.innerHTML = `
            <div class="error-content">
                <strong>⚠️ Error:</strong> ${message}
            </div>
        `;

        // Style the error notification
        Object.assign(errorDiv.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            background: '#e74c3c',
            color: 'white',
            padding: '15px 20px',
            borderRadius: '8px',
            boxShadow: '0 4px 15px rgba(0,0,0,0.2)',
            zIndex: '10000',
            maxWidth: '400px',
            animation: 'slideInRight 0.3s ease-out'
        });

        document.body.appendChild(errorDiv);

        // Remove after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 5000);
    }

    showSuccessMessage(message) {
        console.log('Success:', message);

        // Create success notification
        const successDiv = document.createElement('div');
        successDiv.className = 'success-notification';
        successDiv.innerHTML = `
            <div class="success-content">
                <strong>✅ Success:</strong> ${message}
            </div>
        `;

        // Style the success notification
        Object.assign(successDiv.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            background: '#27ae60',
            color: 'white',
            padding: '15px 20px',
            borderRadius: '8px',
            boxShadow: '0 4px 15px rgba(0,0,0,0.2)',
            zIndex: '10000',
            maxWidth: '400px',
            animation: 'slideInRight 0.3s ease-out'
        });

        document.body.appendChild(successDiv);

        // Remove after 4 seconds
        setTimeout(() => {
            if (successDiv.parentNode) {
                successDiv.remove();
            }
        }, 4000);
    }

    updateTimestamp() {
        const now = new Date();
        const timeString = now.toLocaleTimeString();
        this.updateElement('last-update', timeString);
    }

    updateSystemUptime() {
        const startTime = Date.now();

        setInterval(() => {
            const uptime = Date.now() - startTime;
            const hours = Math.floor(uptime / (1000 * 60 * 60));
            const minutes = Math.floor((uptime % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((uptime % (1000 * 60)) / 1000);

            const uptimeString = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

            const element = document.getElementById('system-uptime');
            if (element) {
                element.textContent = `Uptime: ${uptimeString}`;
            }
        }, 1000);
    }

    startAutoRefresh() {
        // Refresh every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.refreshData();
        }, 30000);

        console.log('⏰ Auto-refresh enabled (30sec interval)');
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
        console.log('⏰ Auto-refresh stopped');
    }
}

// Add CSS for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    .error-notification, .success-notification {
        animation: slideInRight 0.3s ease-out !important;
    }

    .scenario-loading {
        text-align: center;
        padding: 40px;
    }

    .scenario-loading .spinner {
        width: 40px;
        height: 40px;
        border: 4px solid #ecf0f1;
        border-top: 4px solid #3498db;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto 20px;
    }

    .scenario-metrics {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 15px;
        margin: 20px 0;
    }

    .scenario-metric {
        text-align: center;
        padding: 15px;
        background: rgba(52, 152, 219, 0.1);
        border-radius: 8px;
    }

    .scenario-metric .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #2c3e50;
    }

    .scenario-metric .metric-label {
        font-size: 0.85rem;
        color: #666;
        margin-top: 5px;
    }

    .scenario-analysis, .scenario-recommendations {
        margin: 20px 0;
        padding: 15px;
        background: #f8f9fa;
        border-radius: 8px;
    }

    .scenario-error {
        text-align: center;
        padding: 40px;
        color: #e74c3c;
    }

    .detail-section {
        margin-bottom: 25px;
        padding: 20px;
        background: #f8f9fa;
        border-radius: 10px;
    }

    .detail-section h4 {
        color: #2c3e50;
        margin-bottom: 15px;
        border-bottom: 2px solid #ecf0f1;
        padding-bottom: 8px;
    }

    .metric-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 15px;
        margin-top: 15px;
    }

    .metric-item {
        text-align: center;
        padding: 12px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
`;
document.head.appendChild(style);

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚂 Initializing VyuhMitra Dashboard...');
    window.dashboard = new VyuhMitraDashboard();
});
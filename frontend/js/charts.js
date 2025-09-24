// charts.js - Chart.js integration for simulation

function updateScheduleChart(schedules) {
    const ctx = document.getElementById('scheduleChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: schedules.length ? schedules.map(s => s.train_id) : ['No Data'],
            datasets: [{
                label: 'Deviation (min)',
                data: schedules.length ? schedules.map(s => s.deviation) : [0],
                backgroundColor: schedules.length ? schedules.map(s => s.deviation > 0 ? 'red' : 'green') : ['gray']
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function updatePerformanceChart(kpis) {
    const ctx = document.getElementById('performanceChart').getContext('2d');
    const data = kpis.throughput_metrics ? [
        kpis.throughput_metrics.planned_throughput_trains_per_hour || 0,
        kpis.throughput_metrics.average_headway_minutes || 0,
        kpis.infrastructure_metrics.average_section_speed_kmph || 0,
        kpis.efficiency_score.overall_score || 0
    ] : [0, 0, 0, 0];
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Throughput', 'Headway', 'Speed', 'Efficiency'],
            datasets: [{
                label: 'Performance Metrics',
                data: data,
                borderColor: 'blue'
            }]
        },
        options: {
            responsive: true
        }
    });
}

function updateSimulationChart(kpi_data) {
    const ctx = document.getElementById('simulationChart').getContext('2d');
    const labels = kpi_data.optimization_impact && kpi_data.optimization_impact.success ?
        Object.keys(kpi_data.optimization_impact.optimized_schedule) : ['No Data'];
    const data = kpi_data.optimization_impact && kpi_data.optimization_impact.success ?
        Object.values(kpi_data.optimization_impact.optimized_schedule).map(s => [s.optimized_entry, s.optimized_exit]) : [[0, 0]];
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Entry-Exit Time',
                data: data,
                backgroundColor: 'rgba(75, 192, 192, 0.6)'
            }]
        },
        options: {
            responsive: true,
            indexAxis: 'y',
            scales: {
                x: {
                    min: 0,
                    title: { display: true, text: 'Time (minutes)' }
                }
            }
        }
    });
}

console.log('Charts loaded');
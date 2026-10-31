// Apex Library Management System - Chart.js Initializers

function initDashboardCharts(monthlyLabels, issueData, returnData, catLabels, catCounts) {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#9ca3af' : '#64748b';
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)';

    // 1. Monthly Issues vs Returns Line Chart
    const monthlyCanvas = document.getElementById('monthlyIssueChart');
    if (monthlyCanvas) {
        const ctx = monthlyCanvas.getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: monthlyLabels,
                datasets: [
                    {
                        label: 'Books Issued',
                        data: issueData,
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.35,
                        pointBackgroundColor: '#2563eb',
                        pointRadius: 4,
                        pointHoverRadius: 6
                    },
                    {
                        label: 'Books Returned',
                        data: returnData,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.35,
                        pointBackgroundColor: '#10b981',
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: textColor,
                            font: { family: "'Plus Jakarta Sans', sans-serif", weight: 600, size: 12 }
                        }
                    },
                    tooltip: {
                        backgroundColor: '#0f172a',
                        titleColor: '#ffffff',
                        bodyColor: '#e2e8f0',
                        padding: 12,
                        cornerRadius: 8
                    }
                },
                scales: {
                    x: {
                        grid: { color: gridColor },
                        ticks: { color: textColor, font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: gridColor },
                        ticks: { precision: 0, color: textColor, font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } }
                    }
                }
            }
        });
    }

    // 2. Book Categories Doughnut Chart
    const catCanvas = document.getElementById('categoryPieChart');
    if (catCanvas && catLabels && catLabels.length > 0) {
        const catCtx = catCanvas.getContext('2d');
        new Chart(catCtx, {
            type: 'doughnut',
            data: {
                labels: catLabels,
                datasets: [{
                    data: catCounts,
                    backgroundColor: [
                        '#2563eb',
                        '#06b6d4',
                        '#10b981',
                        '#f59e0b',
                        '#8b5cf6',
                        '#ec4899',
                        '#64748b'
                    ],
                    borderWidth: 2,
                    borderColor: isDark ? '#111827' : '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: textColor,
                            boxWidth: 12,
                            padding: 15,
                            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 }
                        }
                    },
                    tooltip: {
                        backgroundColor: '#0f172a',
                        titleColor: '#ffffff',
                        bodyColor: '#e2e8f0',
                        padding: 10,
                        cornerRadius: 8
                    }
                }
            }
        });
    }
}


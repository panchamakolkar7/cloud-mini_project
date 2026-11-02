// Admin Resource Monitoring & Dashboard Charts
document.addEventListener('DOMContentLoaded', function () {
  // 1. Admin System Storage Donut Chart
  const sysDonutCanvas = document.getElementById('adminStorageDonutChart');
  if (sysDonutCanvas) {
    const usedBytes = parseFloat(sysDonutCanvas.getAttribute('data-used-bytes')) || 0;
    const capacityBytes = parseFloat(sysDonutCanvas.getAttribute('data-capacity-bytes')) || 0;
    const freeBytes = Math.max(0, capacityBytes - usedBytes);

    const usedMB = (usedBytes / (1024 * 1024)).toFixed(1);
    const freeMB = (freeBytes / (1024 * 1024)).toFixed(1);

    new Chart(sysDonutCanvas, {
      type: 'doughnut',
      data: {
        labels: ['Used Storage (MB)', 'Available Capacity (MB)'],
        datasets: [{
          data: [usedMB, freeMB],
          backgroundColor: ['#0d9488', '#e2e8f0'],
          hoverBackgroundColor: ['#0f766e', '#cbd5e1'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: { boxWidth: 12, padding: 14 }
          }
        }
      }
    });
  }

  // 2. Per-User Quota vs Used Storage Bar Chart
  const userBarCanvas = document.getElementById('userQuotaBarChart');
  if (userBarCanvas) {
    fetch('/api/admin/resource-chart-data')
      .then(res => res.json())
      .then(data => {
        new Chart(userBarCanvas, {
          type: 'bar',
          data: {
            labels: data.usernames,
            datasets: [
              {
                label: 'Used (MB)',
                data: data.used_mb,
                backgroundColor: '#0d9488',
                borderRadius: 4
              },
              {
                label: 'Allocated Quota (MB)',
                data: data.quota_mb,
                backgroundColor: '#94a3b8',
                borderRadius: 4
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: {
                beginAtZero: true,
                title: {
                  display: true,
                  text: 'Megabytes (MB)'
                }
              },
              x: {
                grid: { display: false }
              }
            },
            plugins: {
              legend: {
                position: 'top',
                labels: { boxWidth: 12 }
              }
            }
          }
        });
      })
      .catch(err => console.error("Error loading user quota chart data:", err));
  }
});

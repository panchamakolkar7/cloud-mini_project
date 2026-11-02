// User Dashboard Storage Doughnut Chart initialization
document.addEventListener('DOMContentLoaded', function () {
  const chartCanvas = document.getElementById('userStorageDonutChart');
  if (!chartCanvas) return;

  const usedBytes = parseFloat(chartCanvas.getAttribute('data-used-bytes')) || 0;
  const remainingBytes = parseFloat(chartCanvas.getAttribute('data-remaining-bytes')) || 0;
  const usagePercent = parseFloat(chartCanvas.getAttribute('data-usage-percent')) || 0;

  // Convert to Megabytes for friendly chart values
  const usedMB = (usedBytes / (1024 * 1024)).toFixed(2);
  const remainingMB = (remainingBytes / (1024 * 1024)).toFixed(2);

  // Dynamic color based on usage percent
  let usedColor = '#0d9488'; // Teal
  if (usagePercent >= 90) {
    usedColor = '#ef4444'; // Red
  } else if (usagePercent >= 80) {
    usedColor = '#f59e0b'; // Amber / Orange
  }

  new Chart(chartCanvas, {
    type: 'doughnut',
    data: {
      labels: ['Used Storage (MB)', 'Remaining Storage (MB)'],
      datasets: [{
        data: [usedMB, remainingMB],
        backgroundColor: [usedColor, '#e2e8f0'],
        borderWidth: 0,
        hoverOffset: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '76%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            boxWidth: 12,
            padding: 16,
            font: {
              family: 'Inter',
              size: 12
            }
          }
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              return ` ${context.label}: ${context.raw} MB`;
            }
          }
        }
      }
    }
  });
});

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { createChart } from 'lightweight-charts'

const chartContainer = ref(null)
let chartInstance

onMounted(() => {
  chartInstance = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: chartContainer.value.clientHeight,
    layout: {
      background: { type: 'solid', color: '#222' },  // Set to grey background
      textColor: '#FFFFFF',                            // Set axis labels to white
    },
    grid: {
      vertLines: {
        color: '#111',                              // White vertical grid lines
      },
      horzLines: {
        color: '#111',                              // White horizontal grid lines

      },
    },
  })

  const lineSeries = chartInstance.addLineSeries({
    color: '#FFFFFF',  // Set the line color to white for better contrast
  })

  lineSeries.setData([
    { time: '2023-01-01', value: 80.01 },
    { time: '2023-01-02', value: 96.63 },
    { time: '2023-01-03', value: 88.45 },
    { time: '2023-01-04', value: 92.73 },
    { time: '2023-01-05', value: 85.20 },
    { time: '2023-01-06', value: 87.50 },
    { time: '2023-01-07', value: 90.10 },
    { time: '2023-01-08', value: 94.73 },
    { time: '2023-01-09', value: 89.90 },
    { time: '2023-01-10', value: 96.30 },
    { time: '2023-01-11', value: 102.40 },
    { time: '2023-01-12', value: 99.10 },
    { time: '2023-01-13', value: 95.20 },
    { time: '2023-01-14', value: 97.40 },
    { time: '2023-01-15', value: 100.70 },
  ])
})
onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.remove()
  }
})
</script>

<template>
  <div ref="chartContainer" class="chart-container"></div>
</template>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  background-color: #2e2e2e; /* Matches the background of the chart */
  border: 0px solid #444;    /* Optional border to match the LiteGraph style */
}
</style>

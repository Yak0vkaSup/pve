<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { createChart } from 'lightweight-charts'

const chartContainer = ref(null)
let chartInstance

onMounted(() => {
  chartInstance = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: chartContainer.value.clientHeight,
  })

  const lineSeries = chartInstance.addLineSeries()
  lineSeries.setData([
    { time: '2023-01-01', value: 80.01 },
    { time: '2023-01-02', value: 96.63 },
    // Add your chart data here
  ])
})

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.remove()
  }
})
</script>

<template>
  <div ref="chartContainer" style="width: 100%; height: 100%;"></div>
</template>

<style scoped>
div {
  width: 100%;
  height: 100%;
}
</style>

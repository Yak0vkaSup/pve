<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { createChart } from 'lightweight-charts'
import io from 'socket.io-client'

const chartContainer = ref(null)
let chartInstance
let candleSeries
let socket

onMounted(() => {
  // Initialize the chart
  chartInstance = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: chartContainer.value.clientHeight,
    layout: {
      background: { type: 'solid', color: '#222' }, // Set to grey background
      textColor: '#FFFFFF' // Set axis labels to white
    },
    grid: {
      vertLines: {
        color: '#111' // Vertical grid lines
      },
      horzLines: {
        color: '#111' // Horizontal grid lines
      }
    },
    timeScale: {
      timeVisible: true,
      secondsVisible: true
    }
  })

  // Add candlestick series
  candleSeries = chartInstance.addCandlestickSeries({
    upColor: '#4caf50',
    downColor: '#f44336',
    borderDownColor: '#f44336',
    borderUpColor: '#4caf50',
    wickDownColor: '#f44336',
    wickUpColor: '#4caf50'
  })

  // Initialize Socket.IO client
  socket = io('https://pve.finance', { path: '/api/ws/socket.io' })

  socket.on('connect', () => {
    console.log('Connected to server via WebSocket')
    // Fetch data immediately upon connection
  })

  socket.on('disconnect', () => {
    console.log('Disconnected from server')
  })

  // Listen for 'update_chart' event with new data
  socket.on('update_chart', (response) => {
    if (response.status === 'success') {
      updateChartData(response.data)
    } else {
      console.error('Error updating chart:', response.message)
    }
  })

  // Resize chart on window resize
  window.addEventListener('resize', () => {
    chartInstance.resize(chartContainer.value.clientWidth, chartContainer.value.clientHeight)
  })
})

onBeforeUnmount(() => {
  // Clean up the chart instance and Socket.IO connection when the component is unmounted
  if (chartInstance) {
    chartInstance.remove()
  }
  if (socket) {
    socket.disconnect()
  }
})


// Function to update the chart with new data
function updateChartData(fetchedData) {
  if (fetchedData && Array.isArray(fetchedData)) {
    const formattedData = fetchedData.map((candle) => ({
      time: candle.date, // The API returns Unix timestamp
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close
    }))

    // Ensure the data is sorted by time (ascending order)
    formattedData.sort((a, b) => a.time - b.time)

    // Update the chart with the new data
    candleSeries.setData(formattedData)
  } else {
    console.error('Invalid data format:', fetchedData)
  }
}
</script>

<template>
  <div ref="chartContainer" class="chart-container"></div>
</template>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  background-color: #2e2e2e; /* Matches the background of the chart */
  border: 0px solid #444; /* Optional border to match the LiteGraph style */
}
</style>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { createChart } from 'lightweight-charts'

const chartContainer = ref(null)
let chartInstance
let candleSeries

// Function to fetch data from the backend API
async function fetchData() {
  try {
    const response = await fetch('http://127.0.0.1:5000/api/fetch-data', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        symbol: 'DOGSUSDT',
        start_date: '2024-07-29 00:51:00+00',
      }),
    })

    if (!response.ok) {
      throw new Error(`Error: ${response.status}`)
    }

    const data = await response.json()
    console.log('Fetched data:', data)  // Print the fetched data to the console
    return data

  } catch (error) {
    console.error('Error fetching data:', error)
  }
}

onMounted(async () => {
  // Fetch the data from the backend and print it
  const fetchedData = await fetchData()

  // Initialize the chart
  chartInstance = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: chartContainer.value.clientHeight,
    layout: {
      background: { type: 'solid', color: '#222' },  // Set to grey background
      textColor: '#FFFFFF',                          // Set axis labels to white
    },
    grid: {
      vertLines: {
        color: '#111',                               // White vertical grid lines
      },
      horzLines: {
        color: '#111',                               // White horizontal grid lines
      },
    },
    timeScale: {
        timeVisible: true,
        secondsVisible: true,
    },
  })

  // Add candlestick series
  candleSeries = chartInstance.addCandlestickSeries({
    upColor: '#4caf50', downColor: '#f44336', borderDownColor: '#f44336', borderUpColor: '#4caf50', wickDownColor: '#f44336', wickUpColor: '#4caf50',
  })

  // If you want to use the fetched data to update the chart, you can format it like this:
  if (fetchedData && Array.isArray(fetchedData)) {
    const formattedData = fetchedData.map(candle => ({
      time: candle.date, // The API now returns Unix timestamp
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close
    }))
    
    // Ensure the data is sorted by time (ascending order)
    formattedData.sort((a, b) => a.time - b.time)

    // Update the chart with the fetched data
    candleSeries.setData(formattedData)
  }

  // Resize chart on window resize
  window.addEventListener('resize', () => {
    chartInstance.resize(chartContainer.value.clientWidth, chartContainer.value.clientHeight)
  })
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

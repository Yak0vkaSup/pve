<script setup>
import { ref, onMounted, onBeforeUnmount, reactive, watch } from 'vue'
import { createChart } from 'lightweight-charts'
import io from 'socket.io-client'

const chartContainer = ref(null)
let chartInstance
let candleSeries
let socket

// Reactive object to store MA settings
const maSettings = reactive({})

// Map to store line series for MAs dynamically
const lineSeriesMap = {}

// Variable to store fetched data
let fetchedData = []

function getRandomColor() {
  const letters = '0123456789ABCDEF'
  let color = '#'
  for (let i = 0; i < 6; i++ ) {
    color += letters[Math.floor(Math.random() * 16)]
  }
  return color
}

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

  // Get user ID and token from local storage
  const userId = localStorage.getItem('userId')
  const userToken = localStorage.getItem('userToken')

  // Initialize Socket.IO client with query parameters
  socket = io('https://pve.finance', {
    path: '/api/ws/socket.io',
    query: {
      user_id: userId,
      token: userToken
    },
    transports: ['websocket']
  })
  socket.on('connect', () => {
    console.log('Connected to server via WebSocket')
  })

  socket.on('disconnect', () => {
    console.log('Disconnected from server')
  })

  socket.on('reconnect_attempt', () => {
    console.log('Attempting to reconnect...')
  })

  socket.on('connect_error', (error) => {
    console.error('Connection error:', error)
  })

  socket.on('update_chart', (response) => {
    console.log('Response from server:', response)
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

// Watch for changes in MA settings
watch(maSettings, (newSettings) => {
  Object.keys(newSettings).forEach((maName) => {
    const settings = newSettings[maName]

    if (settings.visible) {
      if (!lineSeriesMap[maName]) {
        // Create a new line series for the MA
        const lineSeries = chartInstance.addLineSeries({
          color: settings.color,
          lineWidth: 2,
          title: maName
        })
        lineSeriesMap[maName] = lineSeries

        // Prepare data for this MA
        const maData = fetchedData
          .filter(candle => candle[maName] !== undefined)
          .map((candle) => ({
            time: candle.date,
            value: candle[maName]
          }))

        // Ensure the data is sorted
        maData.sort((a, b) => a.time - b.time)

        // Update the line series data
        lineSeriesMap[maName].setData(maData)
      } else {
        // Update line series options if needed
        lineSeriesMap[maName].applyOptions({
          color: settings.color
        })
      }
    } else {
      // If MA is not visible, remove its series if it exists
      if (lineSeriesMap[maName]) {
        chartInstance.removeSeries(lineSeriesMap[maName])
        delete lineSeriesMap[maName]
      }
    }
  })
}, { deep: true })

function updateChartData(data) {
  fetchedData = data
  if (fetchedData && Array.isArray(fetchedData)) {
    const formattedData = []
    const maNames = new Set()

    fetchedData.forEach((candle) => {
      // Format candlestick data
      formattedData.push({
        time: candle.date, // The API returns Unix timestamp
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close
      })

      // Identify MA names in the candle
      Object.keys(candle).forEach((key) => {
        if (!['date', 'open', 'high', 'low', 'close', 'volume'].includes(key)) {
          maNames.add(key)
        }
      })
    })

    // Update maSettings with new MAs
    maNames.forEach((maName) => {
      if (!maSettings[maName]) {
        // Assign default settings
        maSettings[maName] = {
          color: getRandomColor(),
          visible: true // By default, MAs are visible
        }
      }
    })

    // Remove MAs that are no longer in the data
    Object.keys(maSettings).forEach((maName) => {
      if (!maNames.has(maName)) {
        delete maSettings[maName]
        if (lineSeriesMap[maName]) {
          chartInstance.removeSeries(lineSeriesMap[maName])
          delete lineSeriesMap[maName]
        }
      }
    })

    // Ensure the data is sorted by time (ascending order)
    formattedData.sort((a, b) => a.time - b.time)

    // Update the candlestick data
    candleSeries.setData(formattedData)

    // For each MA, create or update the line series
    Object.keys(maSettings).forEach((maName) => {
      const settings = maSettings[maName]

      if (settings.visible) {
        if (!lineSeriesMap[maName]) {
          // Create a new line series for the MA
          const lineSeries = chartInstance.addLineSeries({
            color: settings.color,
            lineWidth: 2,
            title: maName
          })
          lineSeriesMap[maName] = lineSeries
        } else {
          // Update line series options if needed
          lineSeriesMap[maName].applyOptions({
            color: settings.color
          })
        }

        // Prepare data for this MA
        const maData = fetchedData
          .filter(candle => candle[maName] !== undefined)
          .map((candle) => ({
            time: candle.date,
            value: candle[maName]
          }))

        // Ensure the data is sorted
        maData.sort((a, b) => a.time - b.time)

        // Update the line series data
        lineSeriesMap[maName].setData(maData)
      } else {
        // If MA is not visible, remove its series if it exists
        if (lineSeriesMap[maName]) {
          chartInstance.removeSeries(lineSeriesMap[maName])
          delete lineSeriesMap[maName]
        }
      }
    })
  } else {
    console.error('Invalid data format:', fetchedData)
  }
}
</script>

<template>
  <div ref="chartContainer" class="chart-container">
    <!-- MA Settings Overlay -->
    <div class="ma-settings">
      <div v-for="(settings, maName) in maSettings" :key="maName" class="ma-setting">
        <label>
          <input type="checkbox" v-model="settings.visible" />
          <span>{{ maName }}</span> <!-- Wrapped the label text in a <span> -->
        </label>
        <input type="color" v-model="settings.color" />
      </div>
    </div>
  </div>
</template>


<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  background-color: #2e2e2e;
  border: 0px solid #444;
  position: relative; /* Necessary for positioning the overlay */
}

/* MA Settings Overlay */
.ma-settings {
  z-index: 10; /* Ensures the overlay is above other elements */
  position: absolute;
  top: 8px;
  left: 8px; /* Positioned in the front-left corner */
  background-color: rgba(0, 0, 0, 0.0); /* Transparent background */
  padding: 8px;
  border-radius: 4px;
  max-width: 200px;
  max-height: 80vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ma-setting {
  display: flex;
  align-items: center;
  color: #fff;
}

/* Make the MA label smaller */
.ma-setting label span {
  font-size: 0.9em; /* Adjust as needed */
  margin-left: 8px; /* Space between checkbox and label text */
}

/* Hide the default checkbox */
.ma-setting label input[type="checkbox"] {
  opacity: 0;
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  margin: 0;
  cursor: pointer;
}

/* Create a custom circular checkbox */


/* Change the circle's background when checked */
.ma-setting label input[type="checkbox"]:checked + span::before {
  background-color: grey; /* Grey fill when checked */
}

/* Alternative approach to show the checked state */
.ma-setting label input[type="checkbox"]:checked + span::before {
  /* Add any additional styles for the checked state if needed */
}

/* Adjust the span to accommodate the custom checkbox */
.ma-setting label span {
  position: relative;

  cursor: pointer;
  user-select: none;
}

/* Style the color input to remove white background and stroke */
.ma-setting input[type="color"] {
  width: 14px;
  height: 14px;
  border: none;
  padding: 0;
  margin-left: 20px;
  background: none; /* Remove background */
  cursor: pointer;
  border-radius: 50%; /* Make it circular if desired */
  -webkit-appearance: none;
  appearance: none;
}

/* Remove the default color swatch padding and border */
.ma-setting input[type="color"]::-webkit-color-swatch-wrapper {
  padding: 0;
}

.ma-setting input[type="color"]::-webkit-color-swatch {
  border: none;
  border-radius: 50%;
}

/* Remove focus outline */
.ma-setting input[type="color"]:focus {
  outline: none;
}

/* Optional: Change the cursor to pointer for better UX */
.ma-setting input[type="checkbox"] + span::before {
  cursor: pointer;
}
</style>

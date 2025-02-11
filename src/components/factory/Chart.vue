<script setup>
import { ref, onMounted, onBeforeUnmount, reactive, watch, computed } from 'vue'
import { createChart } from 'lightweight-charts'
import { LineType } from 'lightweight-charts'
import { useWebSocketStore } from '@/stores/websocket.ts';
import { useAuthStore } from '../../stores/auth.ts'
const chartContainer = ref(null)
const isFullscreen = ref(false) // Track fullscreen state
const authStore = useAuthStore()

let chartInstance
let candleSeries
let socket
let volumeSeries

// Access the WebSocket store
const wsStore = useWebSocketStore();

// Reactive object to store MA settings
const maSettings = reactive({})

// Map to store line series for MAs dynamically
const lineSeriesMap = {}

// Variable to store fetched data
let fetchedData = []

// Function to generate a random color
function getRandomColor() {
  const letters = '0123456789ABCDEF'
  let color = '#'
  for (let i = 0; i < 6; i++ ) {
    color += letters[Math.floor(Math.random() * 16)]
  }
  return color
}

// Load saved MA colors from localStorage
const savedMaColors = JSON.parse(localStorage.getItem('maColors') || '{"order_1":"#28914d","order_2":"#28914d","order_3":"#28914d","order_4":"#28914d","order_5":"#28914d"}')
const precision = computed(() => wsStore.precision ?? 2); // Default to 2 if null
const minMove = computed(() => wsStore.minMove ?? 0.01); // Default to 0.01 if null

// Watcher to save MA colors to localStorage whenever they change
watch(maSettings, (newSettings) => {
  const maColorsToSave = {}
  for (const maName in newSettings) {
    maColorsToSave[maName] = newSettings[maName].color
  }
  localStorage.setItem('maColors', JSON.stringify(maColorsToSave))
}, { deep: true })

onMounted(() => {
  document.addEventListener('fullscreenchange', () => {
    isFullscreen.value = !!document.fullscreenElement;
  });
  if (!authStore.isAuthenticated) {
    return
  }
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

  // Add histogram series for volume
  volumeSeries = chartInstance.addHistogramSeries({
    priceFormat: {
      type: 'volume',
    },
    priceScaleId: '', // Place volume on a separate price scale
  });
  volumeSeries.priceScale().applyOptions({
    scaleMargins: {
        top: 0.7, // highest point of the series will be 70% away from the top
        bottom: 0,
    },
  });
  candleSeries.priceScale().applyOptions({
    scaleMargins: {
        top: 0.1, // highest point of the series will be 10% away from the top
        bottom: 0.2, // lowest point will be 20% away from the bottom
    },
  });
  if (!wsStore.isConnected) {
    wsStore.initializeWebSocket();
  }
  // Watch for chartData updates from the WebSocket store
  watch(() => wsStore.chartData, (newData) => {
    if (newData) {
      updateChartData(newData);
    }
  });
  watch([precision, minMove], ([newPrecision, newMinMove]) => {
    if (candleSeries) {
      candleSeries.applyOptions({
        priceFormat: {
          type: 'price',
          precision: newPrecision,
          minMove: newMinMove,
        },
      });
    }
  });
  // Resize chart on window resize
  window.addEventListener('resize', () => {
    chartInstance.resize(chartContainer.value.clientWidth, chartContainer.value.clientHeight)
  })
})

onBeforeUnmount(() => {
  document.removeEventListener('fullscreenchange', () => {
    isFullscreen.value = !!document.fullscreenElement;
  });
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
    const settings = newSettings[maName];

    if (settings.visible) {
      if (!lineSeriesMap[maName]) {
        // Create a new line series for the MA
        const lineSeries = chartInstance.addLineSeries({
          color: settings.color,
          lineWidth: 2,
          title: maName,
        });
        lineSeriesMap[maName] = lineSeries;
      }

      // Prepare data for this MA with gap handling
      const maData = [];
      let nullCounter = 0;
      let lastValidValue = null;

      fetchedData.forEach((candle) => {
        const maValue = candle[maName];

        if (maValue === null || maValue === 0 || maValue === "None") {
          nullCounter++;
          if (nullCounter <= 15) {
            maData.push({
              time: candle.date,
              value: lastValidValue, // Extend the last valid value
              color: "transparent", // Render as transparent to skip visually
            });
          }
        } else {
          nullCounter = 0; // Reset counter
          lastValidValue = maValue; // Update the last valid value
          maData.push({
            time: candle.date,
            value: maValue, // Valid value
          });
        }
      });

      // Ensure the data is sorted
      maData.sort((a, b) => a.time - b.time);

      // Update the line series data
      lineSeriesMap[maName].setData(maData);

      // Apply any updated options like color
      lineSeriesMap[maName].applyOptions({
        color: settings.color,
      });
    } else {
      // If MA is not visible, remove its series if it exists
      if (lineSeriesMap[maName]) {
        chartInstance.removeSeries(lineSeriesMap[maName]);
        delete lineSeriesMap[maName];
      }
    }
  });
}, { deep: true });


function updateChartData(data) {
  fetchedData = data.slice();
  if (fetchedData && Array.isArray(fetchedData)) {
    const formattedData = [];
    const volumeData = [];
    const maNames = new Set();
    const markers = [];

    // Define the prefix mappings
    const prefixMappings = {
      "$": {
        position: 'belowBar',
        shape: 'circle',
        color: 'rgba(0, 150, 136, 1)',
        lineWidth: 3,
      },
      "£": {
        position: 'belowBar',
        shape: 'arrowUp',
        color: 'rgb(34,255,0)',
        lineWidth: 5,
      },
      "@": {
        position: 'aboveBar',
        shape: 'arrowDown',
        color: 'rgb(255,0,0)',
        lineWidth: 5,
      },
      // Add more mappings as needed
    };

    fetchedData.forEach((candle) => {
      const volume = candle.volume;
      const isUpCandle = candle.close > candle.open;
      const colorCandle = isUpCandle ? 'rgba(76, 175, 80, 0.2)' : 'rgba(244, 67, 54, 0.2)';
      const colorVolume = isUpCandle ? 'rgba(76, 175, 80, 0.1)' : 'rgba(244, 67, 54, 0.1)';

      formattedData.push({
        time: candle.date,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
        color: colorCandle,
      });

      volumeData.push({
        time: candle.date,
        value: volume,
        color: colorVolume,
      });

      Object.keys(candle).forEach((key) => {
        if (!["date", "open", "high", "low", "close", "volume"].includes(key)) {
          const prefix = Object.keys(prefixMappings).find((p) => key.startsWith(p));

          if (prefix) {
            if (candle[key]) {
              const markerProps = prefixMappings[prefix];
              const keyWithoutPrefix = key.substring(prefix.length);
              //const text = `${candle[key]}`;
              const text = candle[key] === true ? "signal" : `${candle[key]}`;
              markers.push({
                time: candle.date,
                text: text,
                ...markerProps,
              });
            }
          } else {
            maNames.add(key); // Treat as MA name if no prefix matches
          }
        }
      });
    });
    // Set markers on the candlestick series
    candleSeries.setMarkers(markers);

    // Update MA settings with new MAs or indicators
    maNames.forEach((maName) => {
      if (!maSettings[maName]) {
        maSettings[maName] = {
          color: savedMaColors[maName] || getRandomColor(),
          visible: true,
        };
      }
    });

    // Remove MAs or indicators that are no longer in the data
    Object.keys(maSettings).forEach((maName) => {
      if (!maNames.has(maName)) {
        delete maSettings[maName];
        if (lineSeriesMap[maName]) {
          chartInstance.removeSeries(lineSeriesMap[maName]);
          delete lineSeriesMap[maName];
        }
      }
    });

    // Ensure the data is sorted by time
    formattedData.sort((a, b) => a.time - b.time);

    // Update the candlestick and volume data
    candleSeries.setData(formattedData);
    volumeSeries.setData(volumeData);

    // Update or create line series for MAs
    Object.keys(maSettings).forEach((maName) => {
      const settings = maSettings[maName];

      if (settings.visible) {
        if (!lineSeriesMap[maName]) {
          const lineSeries = chartInstance.addLineSeries({
            color: settings.color,
            lineWidth: 2,
            title: maName,
          });
          lineSeriesMap[maName] = lineSeries;
        }

        const maData = [];
        let nullCounter = 0;
        let lastValidValue = null;

        fetchedData.forEach((candle) => {
          const maValue = candle[maName];

          if (maValue === null || maValue === 0 || maValue === "None") {
            nullCounter++;
            if (nullCounter <= 15) {
              maData.push({
                time: candle.date,
                value: lastValidValue, // Extend the last valid value
                color: "transparent", // Render as transparent to skip visually
              });
            }
          } else {
            nullCounter = 0; // Reset counter
            lastValidValue = maValue; // Update the last valid value
            maData.push({
              time: candle.date,
              value: maValue, // Valid value
            });
          }
        });

        maData.sort((a, b) => a.time - b.time);
        lineSeriesMap[maName].setData(maData);
      } else {
        if (lineSeriesMap[maName]) {
          chartInstance.removeSeries(lineSeriesMap[maName]);
          delete lineSeriesMap[maName];
        }
      }
    });
  } else {
    console.error("Invalid data format:", fetchedData);
  }
}

function toggleFullscreen() {
  if (!isFullscreen.value) {
    chartContainer.value.requestFullscreen();
    isFullscreen.value = true;
  } else {
    document.exitFullscreen();
    isFullscreen.value = false;
  }
}



</script>

<template>
  <div ref="chartContainer" class="chart-container">

    <button @click="toggleFullscreen" class="fullscreen-button">
        {{ isFullscreen ? 'Minimize' : 'Fullscreen' }}
    </button>
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


.chart-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
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
  max-width: 800px;
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


.fullscreen-button {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 10;
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 14px;
  cursor: pointer;
  outline: none;
}

.fullscreen-button:hover {
  background-color: rgba(50, 50, 50, 0.9);
}

.fullscreen-button:active {
  background-color: rgba(30, 30, 30, 1);
}

</style>

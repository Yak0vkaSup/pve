<script setup>
import { ref, onMounted, onBeforeUnmount, reactive, watch, computed } from 'vue'
import { createChart, LineStyle } from 'lightweight-charts'
import { LineType } from 'lightweight-charts'
import { useWebSocketStore } from '@/stores/websocket.ts';
import { useAuthStore } from '../../stores/auth.ts'
import { useGraphStore } from '../../stores/graph.ts'
import { storeToRefs } from 'pinia'
const chartContainer = ref(null)
const isFullscreen = ref(false)

const authStore = useAuthStore()
const graphStore = useGraphStore()
const { selectedTradeTime } = storeToRefs(graphStore)
watch(selectedTradeTime, (newVal) => {
  if (newVal !== null) {
    scrollChartToTime(newVal)
  }
})

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
const orders = computed(() => wsStore.orders ?? []);

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
    crosshair: {
      mode: 0,
    },
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
          //title: maName,
          priceLineVisible: false,
        });
        lineSeriesMap[maName] = lineSeries;
      }

      // Prepare data for this MA with gap handling
      const maData = [];
      let nullCounter = 0;
      let lastValidValue = null;
      let hasValidValue = false; // Track if we've encountered any valid MA value

      fetchedData.forEach((candle) => {
        const maValue = candle[maName];

        if (maValue === null || maValue === 0 || maValue === "None") {
          nullCounter++;
          // Only add transparent points if we've already had valid values
          if (hasValidValue && nullCounter <= 15 && lastValidValue !== null) {
            maData.push({
              time: candle.date,
              value: lastValidValue, // Extend the last valid value
              color: "transparent", // Render as transparent to skip visually
            });
          }
        } else {
          nullCounter = 0; // Reset counter
          lastValidValue = maValue; // Update the last valid value
          hasValidValue = true; // Mark that we now have valid data
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

// Глобальная переменная для хранения line-series ордеров
const orderLineSeriesMap = {};
function clearOrderLineSeries() {
  Object.keys(orderLineSeriesMap).forEach(orderId => {
    chartInstance.removeSeries(orderLineSeriesMap[orderId]);
    delete orderLineSeriesMap[orderId];
  });
}

function updateChartData(data) {
  clearOrderLineSeries();
  fetchedData = data.slice();
  if (!fetchedData || !Array.isArray(fetchedData) || fetchedData.length === 0) {
    console.error("Invalid or empty data:", fetchedData);
    return;
  }

  // --- Хелпер: удаляет дубликаты по времени и сортирует массив по возрастанию времени
  function removeDuplicatesAndSort(arr) {
    if (!Array.isArray(arr)) return [];
    // сортируем по времени
    arr.sort((a, b) => a.time - b.time);
    const result = [];
    // если встречаем маркеры с одинаковым временем, добавляем небольшой оффсет (например, 1 секунда)
    for (const marker of arr) {
      let adjustedMarker = { ...marker };
      // если предыдущий маркер уже имеет такое же время, сдвигаем новый маркер
      if (result.length > 0 && adjustedMarker.time === result[result.length - 1].time) {
        let newTime = adjustedMarker.time + 1; // +1 секунда
        // проверяем, что новый тайм не повторяется среди уже сохранённых маркеров
        while (result.some(m => m.time === newTime)) {
          newTime++;
        }
        adjustedMarker.time = newTime;
      }
      result.push(adjustedMarker);
    }
    return result;
  }


  // --- Обработка свечей
  const formattedData = [];
  const volumeData = [];
  const maNames = new Set();
  const candleMarkers = [];

  // Маппинг для маркеров свечей
  const prefixMappings = {
    "$": { position: 'belowBar', shape: 'circle', color: 'rgba(0, 150, 136, 1)', lineWidth: 3 },
    "£": { position: 'belowBar', shape: 'arrowUp', color: 'rgb(34,255,0)', lineWidth: 5 },
    "@": { position: 'aboveBar', shape: 'arrowDown', color: 'rgb(255,0,0)', lineWidth: 5 },
  };

  fetchedData.forEach(candle => {
    // Проверяем обязательные поля
    if (
      candle.date == null ||
      candle.open == null ||
      candle.high == null ||
      candle.low == null ||
      candle.close == null
    ) {
      console.warn("Skipping candle due to missing mandatory fields:", candle);
      return;
    }
    formattedData.push({
      time: candle.date, // ожидается Unix timestamp (в секундах)
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
      color: candle.close > candle.open
        ? 'rgba(76, 175, 80, 0.2)'
        : 'rgba(244, 67, 54, 0.2)',
    });
    if (candle.volume != null) {
      volumeData.push({
        time: candle.date,
        value: candle.volume,
        color: candle.close > candle.open
          ? 'rgba(76, 175, 80, 0.1)'
          : 'rgba(244, 67, 54, 0.1)',
      });
    }
    // Обработка дополнительных ключей для маркеров
    Object.keys(candle).forEach(key => {
      if (!["date", "open", "high", "low", "close", "volume"].includes(key)) {
        const prefix = Object.keys(prefixMappings).find(p => key.startsWith(p));
        if (prefix && candle[key]) {
          const markerProps = prefixMappings[prefix];
          const text = candle[key] === true ? "signal" : `${candle[key]}`;
          candleMarkers.push({
            time: candle.date,
            text: '',
            ...markerProps
          });
        } else {
          maNames.add(key);
        }
      }
    });
  });

  const safeFormattedData = removeDuplicatesAndSort(formattedData);
  const safeVolumeData = removeDuplicatesAndSort(volumeData);
  const safeCandleMarkers = removeDuplicatesAndSort(candleMarkers);

  // --- Функция для формирования точек ордер-линий
  function getOrderLineSegments(order) {
    const segments = [];
    const toTimestamp = (t) => {
      const ts = Math.floor(new Date(t).getTime() / 1000);
      return isNaN(ts) ? null : ts;
    };

    // Если order.price отсутствует, используем fallback (0)
    const orderPrice = (order.price != null) ? order.price : 0;
    const start = toTimestamp(order.time_created);
    if (start === null) {
      console.error("Invalid order.time_created", order);
      return [];
    }

    if (order.modifications && order.modifications.length > 0) {
      const mods = order.modifications.slice().sort((a, b) => new Date(a.time_modified) - new Date(b.time_modified));
      const initialPrice = (mods[0].previous_price != null) ? mods[0].previous_price : orderPrice;
      segments.push({ time: start, value: initialPrice });
      mods.forEach((mod, i) => {
        const modTime = toTimestamp(mod.time_modified);
        if (modTime === null) {
          console.warn("Skipping modification with invalid time:", mod);
          return;
        }
        let newPrice;
        if (i < mods.length - 1) {
          newPrice = (mods[i + 1].previous_price != null) ? mods[i + 1].previous_price : orderPrice;
        } else {
          newPrice = orderPrice;
        }
        segments.push({ time: modTime, value: newPrice });
      });
    } else {
      segments.push({ time: start, value: orderPrice });
    }

    const finalTime = toTimestamp(order.time_executed || order.time_cancelled || new Date().toISOString());
    segments.push({ time: finalTime, value: orderPrice });
    return removeDuplicatesAndSort(segments);
  }

  // --- Обработка ордеров
  const orderMarkers = [];
  orders.value.forEach(order => {
    const createdTime = Math.floor(new Date(order.time_created).getTime() / 1000);
    if (order.time_executed && order.status === "executed") {
      const executedTime = Math.floor(new Date(order.time_executed).getTime() / 1000);
      if (order.direction) {
        orderMarkers.push({
          time: executedTime,
          text: `${order.quantity}`,
          position: 'belowBar',
          shape: 'arrowUp',
          color: 'green',
          lineWidth: 3,
        });
      } else {
        orderMarkers.push({
          time: executedTime,
          text: `${order.quantity}`,
          position: 'aboveBar',
          shape: 'arrowDown',
          color: 'red',
          lineWidth: 3,
        });
      }
    }
    if (order.type === "limit" || order.order_category === "conditional") {
      const segments = getOrderLineSegments(order);
      if (segments.length < 2) {
        console.warn("Not enough segments for order", order);
        return;
      }
      let lineSeries = orderLineSeriesMap[order.id];
      if (!lineSeries) {
        lineSeries = chartInstance.addLineSeries({
          color: order.direction ? 'green' : 'red',
          lineWidth: 1,
          lastValueVisible: false,
          priceLineVisible: false,
          lineStyle: (order.order_category === "conditional") ? 2 : 0,
          lineType: 1, // WithSteps
        });
        orderLineSeriesMap[order.id] = lineSeries;
      }
      try {
        lineSeries.setData(segments);
      } catch (e) {
        console.error("Error setting order line data", e, segments);
      }
    }
  });

  const mergedMarkers = removeDuplicatesAndSort([...orderMarkers, ...safeCandleMarkers]);
  try {
    candleSeries.setMarkers(mergedMarkers);
  } catch (e) {
    console.error("Error setting markers", e, mergedMarkers);
  }

  try {
    candleSeries.setData(safeFormattedData);
  } catch (e) {
    console.error("Error setting candlestick data", e, safeFormattedData);
  }
  try {
    volumeSeries.setData(safeVolumeData);
  } catch (e) {
    console.error("Error setting volume data", e, safeVolumeData);
  }

  // --- Обработка MA-линий
  maNames.forEach(maName => {
    if (!maSettings[maName]) {
      maSettings[maName] = {
        color: savedMaColors[maName] || getRandomColor(),
        visible: true,
      };
    }
  });
  Object.keys(maSettings).forEach(maName => {
    if (!maNames.has(maName)) {
      delete maSettings[maName];
      if (lineSeriesMap[maName]) {
        chartInstance.removeSeries(lineSeriesMap[maName]);
        delete lineSeriesMap[maName];
      }
    }
  });
  Object.keys(maSettings).forEach(maName => {
    const settings = maSettings[maName];
    if (settings.visible) {
      if (!lineSeriesMap[maName]) {
        const lineSeries = chartInstance.addLineSeries({
          color: settings.color,
          lineWidth: 2,
          priceLineVisible: false,
        });
        lineSeriesMap[maName] = lineSeries;
      }
      const maData = [];
      let nullCounter = 0;
      let lastValidValue = null;
      let hasValidValue = false; // Track if we've encountered any valid MA value
      
      fetchedData.forEach(candle => {
        const maValue = candle[maName];
        if (maValue === null || maValue === 0 || maValue === "None") {
          nullCounter++;
          // Only add transparent points if we've already had valid values
          if (hasValidValue && nullCounter <= 15 && lastValidValue !== null) {
            maData.push({
              time: candle.date,
              value: lastValidValue,
              color: "transparent",
            });
          }
        } else {
          nullCounter = 0;
          lastValidValue = maValue;
          hasValidValue = true; // Mark that we now have valid data
          maData.push({
            time: candle.date,
            value: maValue,
          });
        }
      });
      const safeMaData = removeDuplicatesAndSort(maData);
      try {
        lineSeriesMap[maName].setData(safeMaData);
        lineSeriesMap[maName].applyOptions({ color: settings.color });
      } catch (e) {
        console.error("Error setting MA data", e, safeMaData);
      }
    } else {
      if (lineSeriesMap[maName]) {
        chartInstance.removeSeries(lineSeriesMap[maName]);
        delete lineSeriesMap[maName];
      }
    }
  });
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
function scrollChartToTime(timeInSeconds) {
  if (!chartInstance) return;
  const timeScale = chartInstance.timeScale();

  // Get the currently visible logical range (this is in "logical" space)
  const currentVisibleLogicalRange = timeScale.getVisibleLogicalRange();
  if (!currentVisibleLogicalRange) return;

  // Calculate the width of the current range.
  const rangeWidth = currentVisibleLogicalRange.to - currentVisibleLogicalRange.from;

  // Convert the target time to a coordinate, then to a logical index.
  const coordinate = timeScale.timeToCoordinate(timeInSeconds);
  if (coordinate === null) {
    console.warn('Target time is out of range.');
    return;
  }
  const targetLogical = timeScale.coordinateToLogical(coordinate);

  // Center the target time by creating a new range
  const newFrom = targetLogical - rangeWidth / 2;
  const newTo   = targetLogical + rangeWidth / 2;
  timeScale.setVisibleLogicalRange({ from: newFrom, to: newTo });
}

const filteredMaSettings = computed(() => {
  const filtered = {}
  Object.keys(maSettings).forEach(key => {
    // Если ключ определён и не начинается с "$" – оставляем его
    if (key && !key.startsWith('$')) {
      filtered[key] = maSettings[key]
    }
  })
  return filtered
})

</script>

<template>
  <div ref="chartContainer" class="chart-container">

    <button @click="toggleFullscreen" class="fullscreen-button">
        {{ isFullscreen ? 'Minimize' : 'Fullscreen' }}
    </button>
    <!-- MA Settings Overlay -->
    <div class="ma-settings">
      <div v-for="(settings, maName) in filteredMaSettings" :key="maName" class="ma-setting">
        <label>
          <input type="checkbox" v-model="settings.visible" />
          <span>{{ maName }}</span>
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

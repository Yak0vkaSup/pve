<!-- src/components/Logs.vue -->
<template>
  <div class="logs-container">
    <div class="logs-header" @click="toggleLogs">
      <span>Logs</span>
      <span class="toggle-icon">{{ showLogs ? '▼' : '▲' }}</span>
    </div>
    <div class="logs-content" v-show="showLogs" ref="logsContent">
      <div
        v-for="(log, index) in logs"
        :key="index"
        class="log-message"
        :style="{ color: getTextColor(log.level, log.message) }"
      >
        <span
          class="timestamp"
          :style="{ color: getTimestampColor(index) }"
        >
          {{ formatTimestamp(log.timestamp) }}
        </span>
        <span class="message">{{ log.message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useWebSocketStore } from '@/stores/websocket';

const wsStore = useWebSocketStore();

const logs = computed(() => wsStore.logs);

function formatTimestamp(timestamp: Date) {
  if (isNaN(timestamp.getTime())) {
    return '';
  }
  return timestamp.toLocaleTimeString();
}

function getTextColor(level: string, message: string) {
  if (message.startsWith('Executing')) {
    return '#b0e0ff'; // Light blue for "Executing" messages
  }
  switch (level.toUpperCase()) {
    case 'INFO':
      return '#fff'; // Light green
    case 'WARNING':
      return '#fffdb0'; // Light yellow
    case 'ERROR':
      return '#F77'; // Red
    default:
      return '#fff'; // Default text color (white)
  }
}

const timestampColors = [
  '#FF8A80', // Light Red
  '#FF80AB', // Pink
  '#EA80FC', // Purple
  '#B388FF', // Deep Purple
  '#8C9EFF', // Indigo
  '#82B1FF', // Blue
  '#80D8FF', // Light Blue
  '#84FFFF', // Cyan
  '#A7FFEB', // Teal
  '#B9F6CA', // Green
  '#CCFF90', // Light Green
  '#FFFF8D', // Yellow
  '#FFE57F', // Amber
  '#FFD180', // Orange
  '#FF9E80', // Deep Orange
];

function getTimestampColor(index: number) {
  const colorIndex = index % timestampColors.length;
  return timestampColors[colorIndex];
}

const showLogs = ref(false);

function toggleLogs() {
  showLogs.value = !showLogs.value;
}

// Auto-scroll to the latest log
const logsContent = ref<HTMLElement | null>(null);

watch(
  () => logs.value.length,
  () => {
    if (logsContent.value) {
      logsContent.value.scrollTop = logsContent.value.scrollHeight;
    }
  }
);
</script>

<style scoped>
.logs-container {
  position: fixed;
  bottom: 0;
  right: 0;
  width: 100%;
  z-index: 1000;
}

.logs-header {
  background-color: var(--color-background);
  color: #fff;
  padding: 10px;
  cursor: pointer;
  user-select: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logs-content {
  max-height: 300px;
  overflow-y: auto;
  background-color: var(--color-background-soft);
}

.log-message {
  padding: 5px;
  border-bottom: 1px solid var(--color-background-mute);
  color: #fff; /* Default text color */
  background-color: var(--color-background);
}

.timestamp {
  margin-right: 5px;
}

.message {
  /* Inherits color from .log-message */
}

.toggle-icon {
  font-size: 14px;
}
</style>

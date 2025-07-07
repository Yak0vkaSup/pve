<template>
  <div class="logs-container">
    <div class="logs-content" ref="logsContent">
      <div
        v-for="(log, index) in logs"
        :key="index"
        class="log-message"
        :style="{ color: getTextColor(log.level, log.message) }"
      >
        <span class="timestamp" :style="{ color: getTimestampColor(index) }">
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
  return isNaN(timestamp.getTime()) ? '' : timestamp.toLocaleTimeString();
}

function getTextColor(level: string, message: string) {
  if (message.startsWith('Executing')) return '#b0e0ff';
  switch (level.toUpperCase()) {
    case 'INFO': return '#fff';
    case 'WARNING': return '#fffdb0';
    case 'ERROR': return '#F77';
    default: return '#fff';
  }
}

const timestampColors = [
  '#FF8A80', '#FF80AB', '#EA80FC', '#B388FF', '#8C9EFF',
  '#82B1FF', '#80D8FF', '#84FFFF', '#A7FFEB', '#B9F6CA',
  '#CCFF90', '#FFFF8D', '#FFE57F', '#FFD180', '#FF9E80',
];

function getTimestampColor(index: number) {
  return timestampColors[index % timestampColors.length];
}

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
  width: 100%;
  height: 600px;
}
.logs-content {
  max-height: 600px;
  overflow-y: auto;
  background-color: var(--color-background-soft, #444);
}
.log-message {
  padding: 5px;
  border-bottom: 1px solid var(--color-background-mute, #555);
  background-color: var(--color-background, #333);
  color: #fff;
}
.timestamp {
  margin-right: 5px;
}
</style>

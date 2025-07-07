<template>
  <div class="bot-logs-container">
    <div class="logs-header">
      <div class="button-container">
        <button @click="refreshLogs" :disabled="loading">
          <span v-if="loading">Loading...</span>
          <span v-else>Refresh</span>
        </button>
        <select v-model="selectedLimit" @change="refreshLogs">
          <option value="25">Last 25</option>
          <option value="50">Last 50</option>
          <option value="100">Last 100</option>
          <option value="200">Last 200</option>
        </select>
      </div>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <div v-if="logsData && logsData.totalLogs !== undefined" class="logs-info">
      <div class="info-card">
        <div class="info-label">Total Logs</div>
        <div class="info-value">{{ logsData.totalLogs }}</div>
      </div>
      <div class="info-card">
        <div class="info-label">Showing</div>
        <div class="info-value">{{ logsData.logs.length }}</div>
      </div>
    </div>

    <div v-if="loading && !logsData" class="loading-message">
      Loading logs...
    </div>

    <div v-if="logsData && logsData.logs.length > 0" class="logs-content" ref="logsContent" @scroll="handleScroll">
      <div v-if="loading && logsData.hasMore" class="loading-more">
        Loading more logs...
      </div>
      <div
        v-for="(log, index) in formattedLogs"
        :key="`${log.timestamp}-${index}`"
        class="log-message"
        :style="{ color: getTextColor(log.level, log.message) }"
      >
        <span class="timestamp" :style="{ color: getTimestampColor(index) }">
          {{ formatTimestamp(log.timestamp) }}
        </span>
        <span class="level" :class="log.level.toLowerCase()">
          [{{ log.level }}]
        </span>
        <span class="message">{{ log.message }}</span>
      </div>
    </div>

    <div v-else-if="!loading && logsData" class="no-logs">
      No logs found for this bot.
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick, onUnmounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { toast } from 'vue3-toastify';

const baseURL = import.meta.env.VITE_APP_ENV === 'dev'
  ? 'http://localhost:5001'
  : 'https://pve.finance';

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
}

interface LogsData {
  logs: LogEntry[];
  nextPageCursor?: string;
  hasMore: boolean;
  totalLogs: number;
  currentPage: number;
}

const props = defineProps<{
  botId: number;
}>();

const authStore = useAuthStore();
const pve = { position: toast.POSITION.BOTTOM_RIGHT };

const logsData = ref<LogsData | null>(null);
const loading = ref(false);
const error = ref('');
const selectedLimit = ref('50');
const currentCursor = ref<string | null>(null);
const logsContent = ref<HTMLElement | null>(null);
const isLoadingMore = ref(false);

// Transform logs to the expected format with proper parsing
const formattedLogs = computed(() => {
  if (!logsData.value?.logs) return [];
  
  return logsData.value.logs.map(log => {
    // Clean message to ensure it does not still contain its own timestamp/level prefix
    const cleanedMsg = typeof log.message === 'string'
      ? log.message.replace(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d{3})?\s*-\s*\w+\s*-\s*/, '').trim()
      : log.message;

    return {
      timestamp: new Date(log.timestamp),
      level: log.level,
      message: cleanedMsg || log.message
    };
  });
});

async function fetchLogs(cursor?: string) {
  if (!props.botId || !authStore.userInfo?.id || !authStore.token) return;
  
  if (cursor) {
    isLoadingMore.value = true;
  } else {
    loading.value = true;
  }
  error.value = '';
  
  try {
    const params = new URLSearchParams({
      user_id: authStore.userInfo.id.toString(),
      token: authStore.token,
      limit: selectedLimit.value,
    });
    
    if (cursor) {
      params.append('cursor', cursor);
    }
    
    const response = await fetch(`${baseURL}/api/bots/${props.botId}/logs?${params}`, {
      headers: {
        'Authorization': `Bearer ${authStore.token}`,
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const text = await response.text();
    let result;
    try {
      result = JSON.parse(text);
    } catch (parseError) {
      console.error('Response is not JSON:', text);
      throw new Error(`Server returned invalid JSON. Response: ${text.substring(0, 200)}...`);
    }
    
    if (result.status === 'success') {
      if (cursor && logsData.value) {
        // Store current scroll position
        const scrollContainer = logsContent.value;
        const oldScrollHeight = scrollContainer?.scrollHeight || 0;
        
        // Append new logs when loading more (chronological order)
        logsData.value.logs.push(...result.data.logs);
        logsData.value.nextPageCursor = result.data.nextPageCursor;
        logsData.value.hasMore = result.data.hasMore;
        
        // Maintain scroll position after adding new content
        await nextTick();
        if (scrollContainer) {
          const newScrollHeight = scrollContainer.scrollHeight;
          scrollContainer.scrollTop = newScrollHeight - oldScrollHeight;
        }
      } else {
        // Replace data when refreshing
        logsData.value = result.data;
        // Auto-scroll to bottom on initial load or refresh
        await nextTick();
        scrollToBottom();
      }
      currentCursor.value = result.data.nextPageCursor;
    } else {
      error.value = result.message || 'Failed to fetch logs';
      toast.error(error.value, pve);
    }
  } catch (err: any) {
    error.value = err.message || 'Network error';
    toast.error(error.value, pve);
  } finally {
    loading.value = false;
    isLoadingMore.value = false;
  }
}

function scrollToBottom() {
  if (logsContent.value) {
    logsContent.value.scrollTop = logsContent.value.scrollHeight;
  }
}

function refreshLogs() {
  currentCursor.value = null;
  fetchLogs();
}

async function loadMore() {
  if (currentCursor.value && !isLoadingMore.value) {
    await fetchLogs(currentCursor.value);
  }
}

function handleScroll() {
  if (!logsContent.value || isLoadingMore.value || !logsData.value?.hasMore) return;
  
  // Check if scrolled to top (within 10px threshold)
  if (logsContent.value.scrollTop <= 10) {
    loadMore();
  }
}

function formatTimestamp(timestamp: Date) {
  if (isNaN(timestamp.getTime())) return '';
  return timestamp.toLocaleString();
}

function getTextColor(level: string, message: string) {
  if (message.includes('Executing') || message.includes('Starting')) return '#b0e0ff';
  if (message.includes('Order') || message.includes('Trade')) return '#90EE90';
  switch (level.toUpperCase()) {
    case 'INFO': return '#fff';
    case 'WARNING': return '#fffdb0';
    case 'ERROR': return '#F77';
    case 'DEBUG': return '#ccc';
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

// Watch for new logs and auto-scroll to bottom
watch(
  () => formattedLogs.value.length,
  (newLength, oldLength) => {
    // Only auto-scroll if new logs were added and we're not loading more historical logs
    if (oldLength && newLength > oldLength && !isLoadingMore.value) {
      nextTick(() => scrollToBottom());
    }
  }
);

onMounted(() => {
  fetchLogs();
});

onUnmounted(() => {
  // Clean up any ongoing requests if component is unmounted
});

watch(() => props.botId, () => {
  if (props.botId) {
    refreshLogs();
  }
});
</script>

<style scoped>
.bot-logs-container {
  background: var(--color-background-soft);
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 8px;
}

.logs-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 8px;
}

.button-container {
  display: flex;
  gap: 8px;
}

.button-container button,
.button-container select {
  padding: 10px 20px;
  background-color: #222222;
  color: #fff;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s ease;
  font-size: 12px;
}

.button-container button:hover:not(:disabled),
.button-container select:hover {
  background-color: #353535;
}

.button-container button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  background: var(--color-background);
  color: #F77;
  padding: 8px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  margin-bottom: 8px;
  font-size: 12px;
}

.loading-message {
  text-align: center;
  color: var(--color-heading);
  opacity: 0.7;
  padding: 20px;
  font-style: italic;
  font-size: 12px;
}

.logs-info {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.info-card {
  background: var(--color-background);
  padding: 8px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  text-align: center;
  flex: 1;
}

.info-label {
  color: var(--color-heading);
  font-size: 10px;
  text-transform: uppercase;
  margin-bottom: 4px;
  opacity: 0.7;
}

.info-value {
  color: var(--color-heading);
  font-size: 14px;
  font-weight: bold;
}

.logs-content {
  max-height: 400px;
  overflow-y: auto;
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 4px;
}

.loading-more {
  text-align: center;
  color: var(--color-heading);
  opacity: 0.7;
  padding: 10px;
  font-size: 12px;
  font-style: italic;
  border-bottom: 1px solid var(--color-border);
}

.log-message {
  padding: 5px;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-heading);
  font-family: monospace;
  font-size: 12px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.log-message:last-child {
  border-bottom: none;
}

.timestamp {
  font-weight: bold;
  white-space: nowrap;
  flex-shrink: 0;
}

.level {
  font-weight: bold;
  white-space: nowrap;
  flex-shrink: 0;
  min-width: 60px;
}

.level.info {
  color: #4CAF50;
}

.level.warning {
  color: #FF9800;
}

.level.error {
  color: #F44336;
}

.level.debug {
  color: #9E9E9E;
}

.message {
  word-break: break-word;
  flex: 1;
}

.no-logs {
  text-align: center;
  color: var(--color-heading);
  opacity: 0.7;
  padding: 20px;
  font-style: italic;
  font-size: 12px;
}
</style> 
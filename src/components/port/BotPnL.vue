<template>
  <div class="bot-pnl-container">
    <div class="pnl-header">
      <h3>Trading History & PnL</h3>
      <div class="button-container">
        <button @click="refreshPnL" :disabled="loading">
          <span v-if="loading">Loading...</span>
          <span v-else>Refresh</span>
        </button>
        <select v-model="selectedLimit" @change="refreshPnL">
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

    <div v-if="pnlData && pnlData.summary" class="summary-cards">
      <div class="summary-card">
        <div class="summary-label">Total PnL</div>
        <div class="summary-value" :class="{ positive: pnlData.summary.totalPnl >= 0, negative: pnlData.summary.totalPnl < 0 }">
          {{ formatPnL(pnlData.summary.totalPnl) }}
        </div>
      </div>
      <div class="summary-card">
        <div class="summary-label">Total Trades</div>
        <div class="summary-value">{{ pnlData.summary.totalTrades }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">Winning Trades</div>
        <div class="summary-value">{{ pnlData.summary.winningTrades }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">Win Rate</div>
        <div class="summary-value">{{ pnlData.summary.winRate }}%</div>
      </div>
    </div>



    <div v-if="pnlData && pnlData.trades.length > 0" class="trades-table">
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Side</th>
            <th>Quantity</th>
            <th>Entry Price</th>
            <th>Exit Price</th>
            <th>PnL</th>
            <th>Order Type</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="trade in pnlData.trades" :key="trade.orderId" class="trade-row">
            <td class="trade-time">{{ formatTime(trade.createdTime) }}</td>
            <td class="trade-side" :class="trade.side.toLowerCase()">{{ trade.side }}</td>
            <td class="trade-quantity">{{ trade.closedSize }}</td>
            <td class="trade-price">{{ formatPrice(trade.avgEntryPrice) }}</td>
            <td class="trade-price">{{ formatPrice(trade.avgExitPrice) }}</td>
            <td class="trade-pnl" :class="{ positive: parseFloat(trade.closedPnl) >= 0, negative: parseFloat(trade.closedPnl) < 0 }">
              {{ formatPnL(trade.closedPnl) }}
            </td>
            <td class="trade-type">{{ trade.orderType }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else-if="!loading && pnlData" class="no-trades">
      No trading history found for this bot.
    </div>

    <div v-if="pnlData && pnlData.nextPageCursor" class="pagination">
      <button @click="loadMore" :disabled="loading">
        Load More
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { toast } from 'vue3-toastify';

const baseURL = import.meta.env.VITE_APP_ENV === 'dev'
  ? 'http://localhost:5001'
  : 'https://pve.finance';

interface PnLTrade {
  orderId: string;
  symbol: string;
  side: string;
  qty: string;
  orderPrice: string;
  orderType: string;
  closedSize: string;
  avgEntryPrice: string;
  avgExitPrice: string;
  closedPnl: string;
  leverage: string;
  createdTime: string;
  updatedTime: string;
}

interface PnLSummary {
  totalPnl: number;
  totalTrades: number;
  winningTrades: number;
  winRate: number;
}

interface PnLData {
  symbol: string;
  trades: PnLTrade[];
  nextPageCursor?: string;
  summary: PnLSummary;
  dataUpTo?: string;
  tradingPeriod?: {
    startTime: string;
    endTime: string;
  };
}

const props = defineProps<{
  botId: number;
}>();

const emit = defineEmits<{
  tradingPeriodUpdate: [data: { tradingPeriod?: { startTime: string; endTime: string }; dataUpTo?: string }]
}>();

const authStore = useAuthStore();
const pve = { position: toast.POSITION.BOTTOM_RIGHT };

const pnlData = ref<PnLData | null>(null);
const loading = ref(false);
const error = ref('');
const selectedLimit = ref('50');
const currentCursor = ref<string | null>(null);

async function fetchPnL(cursor?: string) {
  if (!props.botId || !authStore.userInfo?.id || !authStore.token) return;
  
  loading.value = true;
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
    
    const response = await fetch(`${baseURL}/api/bots/${props.botId}/pnl?${params}`, {
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
      if (cursor && pnlData.value) {
        // Append new trades when loading more
        pnlData.value.trades.push(...result.data.trades);
        pnlData.value.nextPageCursor = result.data.nextPageCursor;
      } else {
        // Replace data when refreshing
        pnlData.value = result.data;
        // Emit trading period data
        emit('tradingPeriodUpdate', {
          tradingPeriod: result.data.tradingPeriod,
          dataUpTo: result.data.dataUpTo
        });
      }
      currentCursor.value = result.data.nextPageCursor;
    } else {
      error.value = result.message || 'Failed to fetch PnL data';
      toast.error(error.value, pve);
    }
  } catch (err: any) {
    error.value = err.message || 'Network error';
    toast.error(error.value, pve);
  } finally {
    loading.value = false;
  }
}

function refreshPnL() {
  currentCursor.value = null;
  fetchPnL();
}

function loadMore() {
  if (currentCursor.value) {
    fetchPnL(currentCursor.value);
  }
}

function formatTime(timestamp: string | number): string {
  let date: Date;
  
  if (typeof timestamp === 'string') {
    // If it's a string, it might be a timestamp in milliseconds or ISO string
    if (/^\d+$/.test(timestamp)) {
      // Pure number string - treat as milliseconds
      date = new Date(parseInt(timestamp));
    } else {
      // ISO string or other format
      date = new Date(timestamp);
    }
  } else {
    // It's a number - treat as milliseconds
    date = new Date(timestamp);
  }
  
  return date.toLocaleString();
}

function formatPrice(price: string): string {
  return parseFloat(price).toFixed(4);
}

function formatPnL(pnl: string | number): string {
  const value = typeof pnl === 'string' ? parseFloat(pnl) : pnl;
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(4)}`;
}

onMounted(() => {
  fetchPnL();
});

watch(() => props.botId, () => {
  if (props.botId) {
    refreshPnL();
  }
});
</script>

<style scoped>
.bot-pnl-container {
  background: var(--color-background-soft);
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 8px;
}

.pnl-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.pnl-header h3 {
  color: var(--color-heading);
  margin: 0;
  font-size: 16px;
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

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
  margin-bottom: 8px;
}

.summary-card {
  background: var(--color-background);
  padding: 8px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  text-align: center;
}

.summary-label {
  color: var(--color-heading);
  font-size: 10px;
  text-transform: uppercase;
  margin-bottom: 4px;
  opacity: 0.7;
}

.summary-value {
  color: var(--color-heading);
  font-size: 14px;
  font-weight: bold;
}

.summary-value.positive {
  color: #28a745;
}

.summary-value.negative {
  color: #dc3545;
}

.trades-table {
  overflow-x: auto;
}

.trades-table table {
  width: 100%;
  border-collapse: collapse;
  color: var(--color-heading);
}

.trades-table th {
  background: var(--color-background);
  padding: 8px;
  text-align: center;
  border: 1px solid var(--color-border);
  font-size: 12px;
  text-transform: uppercase;
  color: var(--color-heading);
  opacity: 0.8;
}

.trades-table td {
  padding: 8px;
  border: 1px solid var(--color-border);
  font-size: 12px;
  text-align: center;
}

.trade-row:hover {
  background: var(--color-background-soft);
}

.trade-side.buy {
  color: #28a745;
}

.trade-side.sell {
  color: #dc3545;
}

.trade-pnl.positive {
  color: #28a745;
  font-weight: bold;
}

.trade-pnl.negative {
  color: #dc3545;
  font-weight: bold;
}

.no-trades {
  text-align: center;
  color: var(--color-heading);
  opacity: 0.7;
  padding: 20px;
  font-style: italic;
  font-size: 12px;
}

.pagination {
  text-align: center;
  margin-top: 8px;
}

.pagination button {
  padding: 10px 20px;
  background-color: #222222;
  color: #fff;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s ease;
  font-size: 12px;
}

.pagination button:hover:not(:disabled) {
  background-color: #353535;
}

.pagination button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}


</style> 
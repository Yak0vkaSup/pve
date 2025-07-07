<script setup lang="ts">
import { computed, onMounted, defineEmits } from 'vue';
import TradeDetailsTable       from './TradeDetailsTable.vue';
import { useBacktestStore }    from '@/stores/backtest';

const store = useBacktestStore();
const emit  = defineEmits(['close']);

/* ---- lifecycle ---- */
onMounted(() => {
  const id = Number(localStorage.getItem('selectedBacktestId') || 0);
  if (id) store.fetchAnalyzerResult(id);
});

/* ---- helpers ---- */
const formatTimestamp = (ts: any): string => {
  const toStr = (d: Date) =>
    d.toLocaleString('en-GB', {
      timeZone: 'UTC',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });

  if (typeof ts === 'number' || !isNaN(Number(ts))) return toStr(new Date(+ts * 1000));
  if (typeof ts === 'string' && !isNaN(Date.parse(ts))) return toStr(new Date(ts));
  return ts;
};

/* ---- derived data ---- */
const currentAnalyzerResult = computed(() => {
  const selectedBacktestId = Number(localStorage.getItem('selectedBacktestId') || 0);
  return store.analyzerById(selectedBacktestId);
});

const summaryMetrics = computed(() => {
  const r: any = currentAnalyzerResult.value || {};
  return {
    symbol                 : r['symbol'],
    'Initial Capital'      : r['Initial Capital'],
    'Final Capital'        : r['Final Capital'],
    'First Date'           : r['First Date'],
    'Last Date'            : r['Last Date'],
    'DF Duration'          : r['DF Duration'],
    'Global Return (%)'    : r['Global Return (%)'],
    'Total PnL'            : r['Total PnL'],
    'Total Fees'           : r['Total Fees'],
    'Total Funding Cost'   : r['Total Funding Cost'],
    'Number of Trades'     : r['Number of Trades'],
    'Win Rate (%)'         : r['Win Rate (%)'],
    'Sharpe Ratio'         : r['Sharpe Ratio'],
    'Max Drawdown (%)'     : r['Max Drawdown (%)'],
    'Average Trade Duration': r['Average Trade Duration'],
    Timeframe              : r['timeframe']
  };
});

const formattedTrades = computed(() => {
  const trades = (currentAnalyzerResult.value && currentAnalyzerResult.value['Trades Details']) || [];
  return trades.map((trade: any) => ({
    ...trade,
    entry_time: formatTimestamp(trade.entry_time),
    exit_time : formatTimestamp(trade.exit_time),
    executed_orders: (trade.executed_orders || trade.orders || []).map((o: any) => ({
      ...o,
      time: formatTimestamp(o.time)
    }))
  }));
});

/* ---- events ---- */
const closeDashboard = () => emit('close');
</script>

<template>
  <div class="dashboard-container">
    <button class="close-button" @click="closeDashboard">×</button>

    <div class="metrics-columns">
      <section class="summary-section">
        <h3>Test Summary</h3>
        <table class="metrics-table">
          <tbody>
            <tr><td><strong>Symbol:</strong></td><td>{{ summaryMetrics['symbol'] }}</td></tr>
            <tr><td><strong>Timeframe:</strong></td><td>{{ summaryMetrics['Timeframe'] }}</td></tr>
            <tr><td><strong>Initial Capital:</strong></td><td>{{ summaryMetrics['Initial Capital'] }} USDT</td></tr>
            <tr><td><strong>Final Capital:</strong></td><td>{{ summaryMetrics['Final Capital'] }} USDT</td></tr>
            <tr><td><strong>First Date:</strong></td><td>{{ summaryMetrics['First Date'] }}</td></tr>
            <tr><td><strong>Last Date:</strong></td><td>{{ summaryMetrics['Last Date'] }}</td></tr>
            <tr><td><strong>DF Duration:</strong></td><td>{{ summaryMetrics['DF Duration'] }}</td></tr>
          </tbody>
        </table>
      </section>

      <section class="global-metrics">
        <h3>Global Metrics</h3>
        <table class="metrics-table">
          <tbody>
            <tr><td><strong>Global Return (%):</strong></td><td>{{ summaryMetrics['Global Return (%)'] }}%</td></tr>
            <tr><td><strong>Total PnL:</strong></td><td>{{ summaryMetrics['Total PnL'] }} USDT</td></tr>
            <tr><td><strong>Total Fees Paid:</strong></td><td>{{ summaryMetrics['Total Fees'] }} USDT</td></tr>
            <tr><td><strong>Total Funding Paid:</strong></td><td>{{ summaryMetrics['Total Funding Cost'] }} USDT</td></tr>
            <tr><td><strong>Number of Trades:</strong></td><td>{{ summaryMetrics['Number of Trades'] }}</td></tr>
            <tr><td><strong>Win Rate (%):</strong></td><td>{{ summaryMetrics['Win Rate (%)'] }}</td></tr>
            <tr><td><strong>Sharpe Ratio:</strong></td><td>{{ summaryMetrics['Sharpe Ratio'] }}</td></tr>
            <tr><td><strong>Max Drawdown (%):</strong></td><td>{{ summaryMetrics['Max Drawdown (%)'] }}</td></tr>
            <tr><td><strong>Average Trade Duration:</strong></td><td>{{ summaryMetrics['Average Trade Duration'] }}</td></tr>
          </tbody>
        </table>
      </section>
    </div>

    <TradeDetailsTable :trades="formattedTrades" />
  </div>
</template>

<style scoped>
.dashboard-container {
  background: var(--color-background-soft);
  color: var(--color-text);
  width: 100%;
  padding: 24px;
  border-radius: 8px;
  position: relative;
}
.close-button {
  position: absolute;
  top: 16px;
  right: 16px;
  background: transparent;
  border: none;
  font-size: 24px;
  color: var(--color-heading);
  cursor: pointer;
}
.metrics-columns {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  margin-bottom: 24px;
}
.summary-section,
.global-metrics {
  flex: 1 1 300px;
}
.metrics-table {
  width: 100%;
  border-collapse: collapse;
}
.metrics-table td {
  border: 1px solid var(--color-border);
  padding: 8px;
}
</style>

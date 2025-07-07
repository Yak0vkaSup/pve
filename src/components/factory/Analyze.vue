<script setup lang="ts">
import { ref, onMounted } from 'vue';
import AnalyzerDashboard        from './AnalyzerDashboard.vue';
import { useBacktestStore }     from '@/stores/backtest';

const store         = useBacktestStore();
const showDashboard = ref(false);

/* open analysis for the chosen back-test */
function openDashboard(id: number) {
  localStorage.setItem('selectedBacktestId', id.toString());  // original side-effect
  store.fetchAnalyzerResult(id);                              // optional pre-fetch
  showDashboard.value = true;
}

onMounted(store.fetchBacktests);
</script>

<template>
  <div>
    <div v-if="!showDashboard">
      <table>
        <thead>
          <tr>
            <th>Strategy</th>
            <th>Symbol</th>
            <th>Timeframe</th>
            <th>Start Date</th>
            <th>End Date</th>
            <th>Last Updated</th>
            <th>Action</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="backtest in store.backtests" :key="backtest.id">
            <td>{{ backtest.graph_name }}</td>
            <td>{{ backtest.symbol }}</td>
            <td>{{ backtest.timeframe }}</td>
            <td>{{ backtest.start_date }}</td>
            <td>{{ backtest.end_date }}</td>
            <td>{{ backtest.updated_at }}</td>
            <td>
              <button
                v-if="backtest.analyzer_result_id"
                @click="openDashboard(backtest.id)"
              >
                View Analysis
              </button>

              <button
                v-else
                @click="store.launchAnalyzer(backtest.id)"
              >
                Launch Analyzer
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showDashboard" class="inline-dashboard-container">
      <AnalyzerDashboard @close="showDashboard = false" />
    </div>
  </div>
</template>

<style scoped>
table {
  width: 100%;
  border-collapse: collapse;
}
th,
td {
  border: 1px solid var(--color-border, #282828);
  padding: 8px;
  text-align: center;
}
button {
  padding: 5px 10px;
  font-size: 14px;
  cursor: pointer;
}

/* Inline dashboard container styling */
.inline-dashboard-container {
  border: 1px solid var(--color-border);
  background-color: var(--color-background-soft);
  position: relative;
  padding: 10px;
  border-radius: 8px;
}
</style>

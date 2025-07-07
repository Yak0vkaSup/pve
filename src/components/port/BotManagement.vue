<template>
  <!-- MAIN TOOLBAR ------------------------------------------------------->
  <div class="button-container">
    <!-- existing bots dropdown -->
    <select
      v-model.number="botsStore.activeBotId"
      @focus="botsStore.loadBots"
      @change="handleBotChange"
      class="select-saved-graph"
    >
      <option disabled value="">Select a bot</option>
      <option v-for="b in botsStore.bots" :key="b.id" :value="b.id">
        {{ b.name }}
      </option>
    </select>

    <!-- start / stop -->
    <button v-if="botsStore.activeBot" @click="botsStore.startBot(botsStore.activeBot.id)">
      Start Bot
    </button>
    <button v-if="botsStore.activeBot" @click="botsStore.stopBot(botsStore.activeBot.id)">
      Stop Bot
    </button>

    <button
      v-if="botsStore.activeBot &&
            ['stopped','error','created','inactive'].includes(botsStore.activeBot.status)"
      @click="confirmDelete"
    >
      Delete Bot
    </button>

    <!-- toggle create form -->
    <button @click="creating = !creating">
      {{ creating ? 'Cancel' : 'Create Bot' }}
    </button>
  </div>

  <!-- ACTIVE-BOT INFO moved to Performance tab -->

  <!-- CREATE-BOT FORM ---------------------------------------------------->
  <div v-if="creating" class="create-form button-container">
    <input v-model="apiKey"    placeholder="API Key"    class="input-graph-name" />
    <input v-model="apiSecret" placeholder="API Secret" class="input-graph-name" />

    <select
      v-model.number="selectedBacktestId"
      @focus="backtestStore.fetchBacktests"
      class="select-saved-graph"
    >
      <option disabled value="">Select strategy</option>
      <option v-for="bt in backtestStore.backtests" :key="bt.id" :value="bt.id">
        {{ bt.graph_name }}
      </option>
    </select>

    <!-- live preview -->
    <span v-if="btMeta.symbol">
      {{ btMeta.symbol }} · {{ btMeta.timeframe }} · {{ btMeta.strategy }}
    </span>

    <button @click="createBot">Confirm</button>
  </div>

  <!-- BOT DATA TABS ------------------------------------------------->
  <div v-if="botsStore.activeBot" class="bot-data-section">
    <div class="tabs">
      <button 
        :class="['tab', { active: activeTab === 'performance' }]"
        @click="activeTab = 'performance'"
      >
        Information
      </button>
      <button 
        :class="['tab', { active: activeTab === 'pnl' }]"
        @click="activeTab = 'pnl'"
      >
        Trading History
      </button>
      <button 
        :class="['tab', { active: activeTab === 'logs' }]"
        @click="activeTab = 'logs'"
      >
        Logs
      </button>
    </div>

    <div class="tab-content">
      <!-- PERFORMANCE TAB -->
      <div v-if="activeTab === 'performance'" class="tab-panel">
        <div class="bot-info">
          <div class="bot-details">
            <p><strong>Name:</strong> {{ botsStore.activeBot.name }}</p>
            <p><strong>Status:</strong> {{ botsStore.activeBot.status }}</p>
            <p><strong>Symbol:</strong> {{ botsStore.activeBot.symbol }}</p>
            <p><strong>Timeframe:</strong> {{ botsStore.activeBot.timeframe }}</p>
            <p><strong>Strategy:</strong> {{ botsStore.activeBot.strategy }}</p>
            <div v-if="tradingPeriodData.tradingPeriod" class="trading-period">
              <p><strong>Trading Period:</strong> 
                {{ formatTime(tradingPeriodData.tradingPeriod.startTime) }} → 
                {{ formatTime(tradingPeriodData.tradingPeriod.endTime) }}
              </p>
            </div>
            <div v-else-if="tradingPeriodData.dataUpTo" class="last-update">
              <p><strong>Last update:</strong> {{ formatTime(tradingPeriodData.dataUpTo) }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- PNL TAB -->
      <div v-if="activeTab === 'pnl'" class="tab-panel">
        <BotPnL :bot-id="botsStore.activeBot.id" @trading-period-update="handleTradingPeriodUpdate" />
      </div>

      <!-- LOGS TAB -->
      <div v-if="activeTab === 'logs'" class="tab-panel">
        <BotLogs :bot-id="botsStore.activeBot.id" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue';
import { toast }      from 'vue3-toastify';
import { useBacktestStore } from '@/stores/backtest';
import { useBotsStore }     from '@/stores/bots';
import BotLogs from './BotLogs.vue';
import BotPnL from './BotPnL.vue';

const backtestStore = useBacktestStore();
const botsStore     = useBotsStore();

const pve = { position: toast.POSITION.BOTTOM_RIGHT };

/* local state */
const creating           = ref(false);
const apiKey             = ref('');
const apiSecret          = ref('');
const selectedBacktestId = ref<number | ''>('');
const btMeta             = ref<{symbol?:string; timeframe?:string; strategy?:string; graph?:any}>({});
const activeTab          = ref('performance');
const tradingPeriodData  = ref<{tradingPeriod?: {startTime: string; endTime: string}; dataUpTo?: string}>({});

/* refresh interval */
let refreshInterval: ReturnType<typeof setInterval> | undefined;
let refreshTimeout : ReturnType<typeof setTimeout>  | undefined;

function refreshActiveBot() {
  if (botsStore.activeBotId) botsStore.setActiveBot(botsStore.activeBotId);
}

onMounted(() => {
  /* align the first run to 5 s past the start of the minute */
  const triggerSecond = 5;
  const now           = new Date();
  const secs          = now.getSeconds();
  const secsUntil     = secs < triggerSecond
    ? triggerSecond - secs
    : 60 - secs + triggerSecond;
  const msToNext      = secsUntil * 1000 - now.getMilliseconds(); // run at mm:05s
  refreshActiveBot();
  refreshTimeout = setTimeout(() => {
    refreshActiveBot();                        // first aligned call
    refreshInterval = setInterval(refreshActiveBot, 60_000);  // then every minute at mm:05s
  }, msToNext);
});

onUnmounted(() => {
  if (refreshTimeout ) clearTimeout(refreshTimeout );
  if (refreshInterval) clearInterval(refreshInterval);
});

/* pull analyzer meta whenever strategy changes */
watch(selectedBacktestId, async id => {
  btMeta.value = {};
  if (!id) return;

  /* pull the record via the NEW endpoint */
  await backtestStore.fetchBacktest(id);
  const bt = backtestStore.backtestById(id);

  if (bt) {
    btMeta.value = {
      symbol   : bt.symbol,
      timeframe: bt.timeframe,
      strategy : bt.graph_name,
      graph    : bt.graph,          // full Blockly/VPL JSON
    };
  } else {
    toast.error('Back-test not found', pve);
  }
});

/* create bot */
async function createBot() {
  if (!apiKey.value || !apiSecret.value || !selectedBacktestId.value) {
    toast.error('Fill API keys and choose a strategy', pve);
    return;
  }

  const name = `${btMeta.value.strategy || 'bot'}-${Date.now()}`;

  await botsStore.createBot(name, {
    api_key    : apiKey.value,
    api_secret : apiSecret.value,
    backtest_id: selectedBacktestId.value,
    ...btMeta.value,               // includes symbol, timeframe, strategy, graph
  });

  apiKey.value = apiSecret.value = '';
  selectedBacktestId.value = '';
  creating.value = false;
}

function confirmDelete() {
  const bot = botsStore.activeBot;
  if (!bot) return;
  if (window.confirm(`Delete bot "${bot.name}" (id ${bot.id})? This cannot be undone.`)) {
    botsStore.deleteBot(bot.id);
  }
}

/* dropdown change */
function handleBotChange() {
  if (botsStore.activeBotId) botsStore.setActiveBot(botsStore.activeBotId);
  // Reset to performance tab when switching bots
  activeTab.value = 'performance';
}

/* handle trading period update from BotPnL */
function handleTradingPeriodUpdate(data: {tradingPeriod?: {startTime: string; endTime: string}; dataUpTo?: string}) {
  tradingPeriodData.value = data;
}

/* format time for display */
function formatTime(timestamp: string | number): string {
  let date: Date;
  
  if (typeof timestamp === 'string') {
    if (/^\d+$/.test(timestamp)) {
      date = new Date(parseInt(timestamp));
    } else {
      date = new Date(timestamp);
    }
  } else {
    date = new Date(timestamp);
  }
  
  return date.toLocaleString();
}

/* live stats */
watch(() => botsStore.activeBotId, id => id && botsStore.fetchStats(id));

/* first load */
botsStore.loadBots();
</script>

<style scoped>
.button-container{
  margin-top: 0.5vh;
  margin-bottom: 0.5vh;
  gap: 1vh;
}



.bot-info {
  margin: 8px 0;
  background: var(--color-background-soft);
  padding: 8px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

.bot-details {
  margin-bottom: 16px;
}

.bot-details p {
  margin: 4px 0;
  font-size: 14px;
}

.performance-data {
  margin-top: 16px;
}

.performance-data h4 {
  margin-bottom: 8px;
  font-size: 16px;
}

.bot-data-section {
  margin: 8px 0;
}

.tabs {
  display: flex;
  margin-bottom: 0.5vh;
}

.tab {
  flex: 1;
  padding: 5px;
  border: none;
  background: var(--color-background);
  color: var(--color-heading);
  cursor: pointer;
  transition: background 0.2s ease;
  font-size: 12px;
}

.tab:hover {
  background: var(--color-background-soft);
}

.tab.active {
  background: var(--color-background-soft);
}

.tab-content {
  background: var(--color-background);
}

.tab-panel {
  background: var(--color-background-soft);
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: monospace;
  font-size: 12px;
  background: var(--color-background);
  color: var(--color-heading);
  padding: 8px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  overflow-x: auto;
}
</style>

import { defineStore } from 'pinia';
import { ref } from 'vue';
import axios from 'axios';
import { toast } from 'vue3-toastify';

const pve = { position: toast.POSITION.BOTTOM_RIGHT };

const baseURL =
  import.meta.env.VITE_APP_ENV === 'dev'
    ? 'http://localhost:5001'
    : 'https://pve.finance';

export interface BacktestRecord {
  id: number;
  graph_name: string;
  symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  updated_at: string;
  analyzer_result_id?: number | null;
}



/** **Only** side-effects live here – UI is none of our business */
export const useBacktestStore = defineStore('backtest', () => {
  /* ---------- state ---------- */
  const backtests          = ref<BacktestRecord[]>([]);
  const analyzerResults    = ref<Record<number, any>>({});  // Cache analyzer results by backtest ID
  const single = ref<Record<number, any>>({});

  /* ---------- helpers ---------- */
  function creds() {
    const id    = localStorage.getItem('userId');
    const token = localStorage.getItem('userToken');
    if (!id || !token) {
      toast.error('User not authenticated', pve);
      return null;
    }
    return { id, token };
  }

  /* ---------- actions ---------- */
  async function fetchBacktests() {
    const c = creds();
    if (!c) return;

    try {
      const { data } = await axios.get(`${baseURL}/api/get-backtests`, {
        params : { user_id: c.id, token: c.token },
        headers: { 'Cache-Control': 'no-store' }
      });
      if (data.status === 'success') {
        backtests.value = data.backtests;
      } else {
        toast.error('Error fetching backtests', pve);
      }
    } catch {
      toast.error('Error fetching backtests', pve);
    }
  }

  async function launchAnalyzer(backtestId: number) {
    const c = creds();
    if (!c) return;

    try {
      await axios.post(
        `${baseURL}/api/launch-analyzer`,
        {
          user_id       : c.id,
          backtest_id   : backtestId,
          initial_capital: 300.0,
          token         : c.token
        },
        { headers: { 'Content-Type': 'application/json' } }
      );
      toast.info('Analyzer launched, waiting for result...', pve);
      pollUntilReady(backtestId);
    } catch (error: any) {
      // Handle rate limit error (429 status code)
      if (error.response?.status === 429) {
        const retryAfter = error.response?.data?.retry_after || 30;
        toast.warning(`Please wait ${retryAfter} seconds before launching analyzer again.`, pve);
      } else {
        toast.error('Error launching analyzer', pve);
      }
    }
  }

  async function fetchAnalyzerResult(backtestId: number) {
    const c = creds();
    if (!c) return;

    // Check if we already have this analyzer result cached
    if (analyzerResults.value[backtestId]) {
      return;
    }

    try {
      const { data } = await axios.get(`${baseURL}/api/get-analyzer-result`, {
        params : { user_id: c.id, backtest_id: backtestId, token: c.token },
        headers: { 'Cache-Control': 'no-store' }
      });
      if (data.status === 'success') {
        analyzerResults.value[backtestId] = data.analyzer_result;  // Cache by backtest ID
      } else {
        toast.error('Error fetching analyzer result', pve);
      }
    } catch {
      toast.error('Error fetching analyzer result', pve);
    }
  }

  /* ---------- private ---------- */
  const pollers = new Map<number, number>();

  function pollUntilReady(id: number) {
    if (pollers.has(id)) return;
    const h = window.setInterval(async () => {
      await fetchBacktests();
      const bt = backtests.value.find(b => b.id === id);
      if (bt?.analyzer_result_id) {
        clearInterval(h);
        pollers.delete(id);
        toast.success('Analyzer result is ready!', pve);
      }
    }, 3_000);
    pollers.set(id, h);
  }

  const analyzerById = (id: number) => analyzerResults.value[id] || null;

  async function fetchBacktest(id: number) {
    if (!id) return;
    const userId = localStorage.getItem('userId');
    const token  = localStorage.getItem('userToken');
    if (!userId || !token) {
      toast.error('User not authenticated', pve);
      return;
    }
    if (single.value[id]) return;               // already cached
    const { data } = await axios.get(`${baseURL}/api/get-backtest`, {
      params: { user_id: userId, token, backtest_id: id },
      headers: { 'Cache-Control': 'no-store' },
    });
    if (data.status === 'success') single.value[id] = data.backtest;
  }

  const backtestById = (id: number) => single.value[id] || null;

  return {
    /* state */
    backtests,
    analyzerResults,  // Export the cached results

    /* actions */
    analyzerById,
    backtestById,
    fetchBacktests,
    fetchBacktest,
    launchAnalyzer,
    fetchAnalyzerResult
  };
});

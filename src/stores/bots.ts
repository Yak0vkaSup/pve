// src/stores/bots.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import axios from 'axios';
import { toast } from 'vue3-toastify';
import { useAuthStore } from '@/stores/auth';

const pve = { position: toast.POSITION.BOTTOM_RIGHT };

const baseURL =
  import.meta.env.VITE_APP_ENV === 'dev'
    ? 'http://localhost:5001'
    : 'https://pve.finance';

interface BotInfo {
  id: number;
  name: string;
  status: string;
  symbol?: string;
  timeframe?: string;
  strategy?: string;
}

interface BotStats {
  performance: any;
  logs: any[];
}

export const useBotsStore = defineStore('bots', () => {
  /* -------------------------------------------------- state */
  const auth         = useAuthStore();
  const bots         = ref<BotInfo[]>([]);
  const activeBotId  = ref<number | null>(null);
  const stats        = ref<Record<number, BotStats>>({});
  const loading      = ref(false);

  /* ------------------------------------------------ helpers */
  function toastErr(msg: string) { toast.error(msg, pve); }
  function toastOk(msg: string)  { toast.success(msg, pve); }

  const userId   = computed(() => auth.userInfo?.id ?? '');
  const userTok  = computed(() => auth.token ?? '');

  function guardAuth(): boolean {
    if (!userId.value || !userTok.value) {
      toastErr('User is not authorised');
      return false;
    }
    return true;
  }

  /* ------------------------------------------------ actions */
  async function loadBots() {
    if (!guardAuth()) return;
    loading.value = true;
    try {
      const { data } = await axios.get(`${baseURL}/api/bots`, {
        params: { user_id: userId.value, token: userTok.value }
      });
      if (data.status === 'success') {
        bots.value = data.bots;
        if (!activeBotId.value && bots.value.length) {
          activeBotId.value = bots.value[0].id;
        }
      } else {
        toastErr(data.message || 'Failed to load bots');
      }
    } catch (e) {
      toastErr('Failed to load bots');
    } finally { loading.value = false; }
  }

  async function createBot(name: string, parameters: any) {
    if (!guardAuth()) return;
    try {
      const { data } = await axios.post(
        `${baseURL}/api/bots`,
        {
          user_id:   userId.value,
          token:     userTok.value,
          name,
          parameters,
        },
        { headers: { 'Content-Type': 'application/json' } }
      );

      if (data.status === 'success') {
        toastOk('Bot created');
        await loadBots();
        activeBotId.value = data.bot_id;
      } else {
        toastErr(data.message);
      }
    } catch (e: any) {
      toastErr(e.message);
    }
  }

  async function startBot(id: number) {
    if (!guardAuth()) return;
    await axios.post(
      `${baseURL}/api/bots/${id}/start`,
      { user_id: userId.value, token: userTok.value },
      { headers: { 'Content-Type': 'application/json' } }
    );
    await loadBots();
  }

  async function stopBot(id: number) {
    if (!guardAuth()) return;
    await axios.post(
      `${baseURL}/api/bots/${id}/stop`,
      { user_id: userId.value, token: userTok.value },
      { headers: { 'Content-Type': 'application/json' } }
    );
    await loadBots();
  }

  async function deleteBot(id: number) {
    if (!guardAuth()) return;
    try {
      await axios.delete(`${baseURL}/api/bots/${id}`, {
        params: { user_id: userId.value, token: userTok.value }
      });
      toastOk(`Bot ${id} deleted`);
      await loadBots();
      if (activeBotId.value === id) {
        activeBotId.value = bots.value.length ? bots.value[0].id : null;
      }
    } catch (e: any) {
      toastErr(e.response?.data?.message || 'Delete failed');
    }
  }


  async function fetchStats(id: number, limit = 100) {
    if (!guardAuth()) return;
    try {
      const { data } = await axios.get(`${baseURL}/api/bots/${id}/stats`, {
        params: { user_id: userId.value, token: userTok.value, limit }
      });
      if (data.status === 'success') {
        stats.value[id] = { performance: data.performance, logs: data.logs };
      }
    } catch (e) {
      console.error('Failed to fetch stats', e);
    }
  }

  function setActiveBot(id: number) {
    activeBotId.value = id;
    fetchStats(id);
  }

  /* computed helper */
  const activeBot = computed(() =>
    bots.value.find(b => b.id === activeBotId.value) || null
  );

  /* ------------------------------------------------ expose */
  return {
    bots,
    activeBotId,
    activeBot,
    stats,
    loading,
    loadBots,
    createBot,
    startBot,
    stopBot,
    fetchStats,
    setActiveBot,
    deleteBot,
  };
});

// src/stores/websocket.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { io, Socket } from 'socket.io-client';
import { toast } from 'vue3-toastify';

interface LogMessage {
  timestamp: Date;
  level: string;
  message: string;
}

interface Order {
  id: string;
  direction: boolean;
  type: string;
  order_category: string;
  price: number;
  quantity: number;
  status: string;
  time_created: string;
  time_executed?: string;
  time_cancelled?: string;
}

const pve = { position: toast.POSITION.BOTTOM_RIGHT };

const baseWSUrl = import.meta.env.VITE_APP_ENV === 'dev'
  ? 'ws://localhost:5001'
  : 'wss://pve.finance';

const socketPath = import.meta.env.VITE_APP_ENV === 'dev'
  ? '/socket.io'
  : '/api/ws/socket.io';

export const useWebSocketStore = defineStore('websocket', () => {
  const socket = ref<Socket | null>(null);
  const isConnected = ref(false);
  const logs = ref<LogMessage[]>([]);
  const chartData = ref<any>(null);
  const precision = ref<number | null>(null);
  const minMove = ref<number | null>(null);
  const orders = ref<Order[]>([]);  // Now typed as Order[]

  function initializeWebSocket() {
    const userId = localStorage.getItem('userId');
    const userToken = localStorage.getItem('userToken');

    if (!userId || !userToken) {
      toast.error("User is not authorised", pve);
      return;
    }

    socket.value = io(baseWSUrl, {
      path: socketPath,
      query: { user_id: userId, token: userToken },
      transports: ['websocket']
    });

    socket.value!.on('connect', () => {
      toast.info('Connected to server via WebSocket', pve);
      isConnected.value = true;
    });

    socket.value!.on('disconnect', () => {
      toast.info('Disconnected from server', pve);
      isConnected.value = false;
    });

    socket.value!.on('reconnect_attempt', () => {
      toast.info('Attempting to reconnect...', pve);
    });

    socket.value!.on('connect_error', (error: any) => {
      toast.error('Connection error: ' + error.message, pve);
    });

    socket.value!.on('log_message', (data: any) => {
      const parsedLog = parseLogMessage(data.message);
      logs.value.push(parsedLog);
    });

    socket.value!.on('update_chart', (response: any) => {
      if (response.status === 'success') {
        chartData.value = response.data;
        precision.value = response.precision;
        minMove.value = response.minMove;
        // Update orders using the new updateOrders function
        updateOrders(response.orders);
        console.log(response.orders)
      } else {
        toast.error('Error updating chart', pve);
      }
    });

    socket.value!.on('compilation_progress', (data: any) => {
      // This will be handled by the graph store
      // We'll emit a custom event that the graph store can listen to
      window.dispatchEvent(new CustomEvent('compilation_progress', { detail: data }));
    });
  }

  function parseLogMessage(logMessage: string): LogMessage {
    const regex = /^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+) - (.*?) - (.*?) - (.*)$/;
    const match = logMessage.match(regex);
    if (match) {
      const timestampStr = match[1]; // e.g., '2024-11-06 17:19:55,657'
      const level = match[3];
      const message = match[4];
      const timestampStrModified = timestampStr.replace(',', '.');
      const timestamp = new Date(timestampStrModified);
      if (isNaN(timestamp.getTime())) {
        return { timestamp: new Date(), level, message };
      }
      return { timestamp, level, message };
    } else {
      return { timestamp: new Date(), level: 'INFO', message: logMessage };
    }
  }

  // New function to update orders using the Order interface
  function updateOrders(newOrders: any) {
    if (Array.isArray(newOrders)) {
      // Perform any validation or transformation if needed
      orders.value = newOrders.map((order) => order as Order);
    } else {
      console.error('Invalid orders format received:', newOrders);
    }
  }

  // Function to manually set chart data from backtest data
  function setChartDataFromBacktest(backtestData: any) {
    if (backtestData && backtestData.backtest_data) {
      chartData.value = backtestData.backtest_data;
      precision.value = backtestData.precision ? parseFloat(backtestData.precision) : 2;
      minMove.value = backtestData.min_move ? parseFloat(backtestData.min_move) : 0.01;
      if (backtestData.orders) {
        updateOrders(backtestData.orders);
      }
    }
  }

  function disconnectWebSocket() {
    if (socket.value) {
      socket.value.disconnect();
      toast.error('Disconnected from WebSocket', pve);
    }
  }

  return {
    socket,
    isConnected,
    logs,
    chartData,
    precision,
    minMove,
    orders,
    initializeWebSocket,
    disconnectWebSocket,
    updateOrders,
    setChartDataFromBacktest,
  };
});

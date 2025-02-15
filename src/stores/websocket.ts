// src/stores/websocket.ts
import { defineStore } from 'pinia';
import { ref, reactive, computed } from 'vue';
import io from 'socket.io-client';
import { toast } from 'vue3-toastify'
const pve = {position: toast.POSITION.BOTTOM_RIGHT}
interface LogMessage {
  timestamp: Date;
  level: string;
  message: string;
}
export const useWebSocketStore = defineStore('websocket', () => {
  const socket = ref(null as any);
  const isConnected = ref(false);
  const logs = ref<LogMessage[]>([]);
  const chartData = ref(null);
  const precision = ref<number | null>(null);
  const minMove = ref<number | null>(null);

  // Function to initialize the WebSocket connection
  function initializeWebSocket() {
    // Get user ID and token from local storage
    const userId = localStorage.getItem('userId');
    const userToken = localStorage.getItem('userToken');

    if (!userId || !userToken) {
      toast.error("User is not authorised", pve);
      return;
    }

    socket.value = io('ws://localhost:3000', {
      path: '/api/ws/socket.io',
      query: {
        user_id: userId,
        token: userToken
      },
      transports: ['websocket']
    });

    socket.value.on('connect', () => {
      toast.info('Connected to server via WebSocket', pve);
      isConnected.value = true;
    });

    socket.value.on('disconnect', () => {
      toast.info('Disconnected from server', pve);
      isConnected.value = false;
    });

    socket.value.on('reconnect_attempt', () => {
      toast.info('Attempting to reconnect...', pve);
    });

    socket.value.on('connect_error', (error: any) => {
      toast.error('Connection error:', pve);
    });

    socket.value.on('log_message', (data: any) => {
      // console.log('Log message received:', data.message);
      const parsedLog = parseLogMessage(data.message);
      logs.value.push(parsedLog);
    });

    socket.value.on('update_chart', (response: any) => {
      if (response.status === 'success') {
        chartData.value = response.data;
        precision.value = response.precision;
        minMove.value = response.minMove;
      } else {
        toast.error('Error updating chart:', pve);
      }
    });
  }

  function parseLogMessage(logMessage: string): LogMessage {
    // Expected format:
    // '2024-11-06 17:19:55,657 - app.nodes.nodes - INFO - Starting graph processing'
    const regex = /^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+) - (.*?) - (.*?) - (.*)$/;
    const match = logMessage.match(regex);
    if (match) {
      const timestampStr = match[1]; // '2024-11-06 17:19:55,657'
      const level = match[3]; // 'INFO'
      const message = match[4]; // 'Starting graph processing'

      // Replace ',' with '.' in the timestamp string
      const timestampStrModified = timestampStr.replace(',', '.');

      // Parse the timestamp
      const timestamp = new Date(timestampStrModified);

      // If parsing failed, timestamp will be Invalid Date
      if (isNaN(timestamp.getTime())) {
        // Handle invalid date
        return {
          timestamp: new Date(), // or handle differently
          level,
          message,
        };
      }

      return {
        timestamp,
        level,
        message,
      };
    } else {
      // If parsing fails, return the current time and the whole message
      return {
        timestamp: new Date(),
        level: 'INFO',
        message: logMessage,
      };
    }
  }


  // Function to disconnect the WebSocket
  function disconnectWebSocket() {
    if (socket.value) {
      socket.value.disconnect();
      toast.error('Disconnected from WebSocket', pve)
    }
  }

  return {
    socket,
    isConnected,
    logs,
    chartData,
    precision,
    minMove,
    initializeWebSocket,
    disconnectWebSocket
  };
});

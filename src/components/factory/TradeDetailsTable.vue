<template>
  <div class="trade-details">
    <h3>Trade Details</h3>
    <table class="trade-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Created</th>
          <th>Executed</th>
          <th>Entry Price</th>
          <th>Exit Price</th>
          <th>Qty</th>
          <th>Fees</th>
          <th>Funding Cost</th>
          <th>Profit</th>
          <th>Return (%)</th>
        </tr>
      </thead>
      <tbody>
        <!-- Add a CSS class "clickable" to the row -->
        <tr
          v-for="(trade, idx) in trades"
          :key="idx"
          class="clickable"
          @click="onTradeClick(trade.entry_time)"
        >
          <td>{{ idx + 1 }}</td>
          <td>{{ trade.entry_time }}</td>
          <td>{{ trade.exit_time }}</td>
          <td>{{ trade.entry_price }}</td>
          <td>{{ trade.exit_price }}</td>
          <td>{{ trade.qty }}</td>
          <td>{{ trade.fees }}</td>
          <td>{{ trade.funding_cost }}</td>
          <td>{{ trade.profit }}</td>
          <td>{{ trade.return_pct }}</td>
        </tr>
      </tbody>
    </table>

    <!-- Orders per trade... -->
    <div
      v-for="(trade, idx) in trades"
      :key="'orders-' + idx"
      class="orders-section"
    >
      <h4>Trade {{ idx + 1 }} Orders</h4>
      <table class="orders-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Time</th>
            <th>Price</th>
            <th>Qty</th>
            <th>Fee</th>
            <th>Side</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(order, oIdx) in trade.executed_orders"
            :key="oIdx"
            class="clickable"
            @click.stop="onOrderClick(order.time)"
          >
            <td>{{ oIdx + 1 }}</td>
            <td>{{ order.time }}</td>
            <td>{{ order.price }}</td>
            <td>{{ order.qty }}</td>
            <td>{{ order.fee }}</td>
            <td>{{ order.side }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useGraphStore } from '@/stores/graph'  // <-- Use your real path
import { ref } from 'vue'

interface Order {
  time: string
  price: number
  qty: number
  fee: number
  side: string
}
interface Trade {
  entry_time: string
  exit_time: string
  entry_price: number
  exit_price: number
  qty: number
  fees: number
  funding_cost: number
  profit: number
  return_pct: string
  executed_orders: Order[]
}

const props = defineProps<{ trades: Trade[] }>()
const graphStore = useGraphStore()

function parseTimeToSeconds(timeStr: string): number | null {
  // Example input: "Tue, 04 Feb 2025 05:05:00 GMT"
  // Remove the weekday and comma:
  const cleaned = timeStr.replace(/^[A-Za-z]{3},\s*/, '').trim();
  const dateObj = new Date(cleaned);
  if (isNaN(dateObj.getTime())) {
    return null;
  }
  return Math.floor(dateObj.getTime() / 1000);
}



function onTradeClick(timeStr: string) {
  const timeSec = parseTimeToSeconds(timeStr)
  if (timeSec !== null) {
    graphStore.setSelectedTradeTime(timeSec)
  }
}

function onOrderClick(timeStr: string) {
  const timeSec = parseTimeToSeconds(timeStr)
  if (timeSec !== null) {
    graphStore.setSelectedTradeTime(timeSec)
  }
}
</script>

<style scoped>
.trade-details {
  margin-top: 20px;
}
.trade-table tbody tr.clickable,
.orders-table tbody tr.clickable {
  cursor: pointer;
  transition: background 0.2s;
}
.trade-table tbody tr.clickable:hover,
.orders-table tbody tr.clickable:hover {
  background: rgba(255, 255, 255, 0.1);
}
.trade-table,
.orders-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 16px;
}
.trade-table th,
.trade-table td,
.orders-table th,
.orders-table td {
  border: 1px solid var(--color-border);
  padding: 8px;
  text-align: center;
}
.orders-section {
  margin-bottom: 20px;
}
</style>

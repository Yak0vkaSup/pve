<template>
  <main class="main-content">
    <div class="chart-container">
      <Chart />
    </div>
    <div class="graph-container">
      <Nodes />
    </div>
  </main>
</template>

<script setup lang="ts">
import Chart from '../components/Chart.vue';
import Nodes from '../components/Nodes.vue';
</script>

<style scoped>

.main-content {
  flex: 1;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.chart-container,
.graph-container {
  flex: 1;
  min-height: 300px;
  width: 100%;
}

canvas {
  width: 100%;
  height: 100%;
  border: 1px solid black;
}
</style>

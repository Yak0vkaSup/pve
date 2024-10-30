<template>
  <main class="main-content">
    <div class="chart-container">
      <Chart />
    </div>
    <div class="buttons-container">
      <Buttons />
    </div>
    <div class="graph-container">
      <Nodes />
    </div>
  </main>
</template>

<script setup lang="ts">
import Chart from '../components/Chart.vue';
import Nodes from '../components/Nodes.vue';
import Buttons from '../components/NodesSettings.vue';
</script>

<style scoped>

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  max-height: 200vh;
  max-width: 100vw;
}

.chart-container,
.graph-container {
  min-height: 40vh;
}

canvas {
  width: 100%;
  height: 100%;
}
</style>

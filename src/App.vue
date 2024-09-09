<script setup lang="ts">
import HelloWorld from './components/HelloWorld.vue'
import HelloLWC from './components/HelloLWC.vue'
</script>

<template>
  <div class="container">
    <div class="chart-container">
      <HelloLWC /> <!-- This is where your chart will be rendered -->
    </div>
    <div class="graph-container">
      <HelloWorld msg="" /> <!-- This is where your LiteGraph.js canvas will be rendered -->
    </div>
  </div>
</template>

<style scoped>
.conghtainer {
  
  flex-direction: column; /* Stack the components vertically */
  gap: 1rem; /* Add space between the components */
}

.chart-container {
  display: flex;
  width: 100%;
  height: 600px; /* Set a fixed height for the chart */
}



canvas {
  width: 100%;
  height: 100%;
  border: 1px solid black; /* Ensure the canvas takes up the full size of its container */
}
</style>

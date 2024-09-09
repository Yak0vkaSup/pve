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

<script setup lang="ts">
import HelloWorld from './components/HelloWorld.vue'
import HelloLWC from './components/HelloLWC.vue'
</script>

<style scoped>
.container {
  display: flex;
  flex-direction: column; /* Stack the components vertically */
  gap: 0.5rem; /* Add space between the components */
  height: 97vh;
  /* Use full viewport height */

}

.chart-container {
  /* height:  100vh; */
  flex-grow: 1;
  width: 100%;
  min-height: 300px;
  height: 100%; /* Occupy 40% of the screen height */
}

.graph-container {
  /* height:  100vh; */
  flex-grow: 1;
  width: 100%;
  min-height: 300px;
  height: 100%; 
  /* Occupy 60% of the screen height */
}

canvas {
  width: 100%;
  height: 100%;
  border: 1px solid black; /* Ensure the canvas takes up the full size of its container */
}
</style>

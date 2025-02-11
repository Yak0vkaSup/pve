<template>
  <main class="main-content">
    <div class="port-page">
<!--      <div v-if="!isFullscreen" class="other-content">
        <div>
          <h2>Bot Management</h2>
          <div>
            <label>Select Bot:</label>
            <select v-model="selectedBot" @change="fetchBotPerformance">
              <option v-for="bot in bots" :key="bot.id" :value="bot.id">
                {{ bot.name }} - {{ bot.status }}
              </option>
            </select>
            <button @click="stopBot">Stop</button>
          </div>

          <h3>Create New Bot</h3>
          <input v-model="newBotName" placeholder="Enter Bot Name">
          <button @click="createBot">Create</button>

          <chart-component v-if="selectedBot" :data="chartData" />
        </div>
      </div>-->
      <div class="chart-container">
        <Chart :is-fullscreen="isFullscreen" @toggleFullscreen="handleFullscreenToggle" />
      </div>

    </div>
  </main>
</template>

<script setup lang="ts">
import Chart from '../components/factory/Chart.vue';
import { ref, computed } from 'vue'
import Logs from '@/components/factory/Logs.vue'
import Nodes from '@/components/factory/Nodes.vue'

const isFullscreen = ref(false) // Track fullscreen state
function handleFullscreenToggle() {
  isFullscreen.value = !isFullscreen.value;
}

</script>

<style scoped>
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  max-height: 200vh;
  max-width: 100vw;
}

.chart-container {
  width: 100%;
  height: 40vh;
  background-color: #2e2e2e;
  border: 0px solid #444;
  position: relative; /* Necessary for positioning the overlay */
}

.chart-container.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: #000;
  z-index: 1000;
}
.graph-container {
  min-height: 50vh;
}

canvas {
  width: 100%;
  height: 100%;
}
</style>

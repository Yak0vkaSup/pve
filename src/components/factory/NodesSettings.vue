<!-- src/components/ButtonControls.vue -->
<template>
  <div class="button-container">
    <input v-model="graphStore.graphName" placeholder="Enter graph name" class="input-graph-name" />

    <button @click="graphStore.saveGraphToServer">Save</button>
    <button @click="graphStore.deleteGraphToServer">Delete</button>

    <select
      v-model="graphStore.selectedGraph"
      @focus="graphStore.fetchSavedGraphs"
      @change="handleGraphChange"
      class="select-saved-graph"
    >
      <option disabled value="">Select a saved graph</option>
      <option v-for="graph in graphStore.savedGraphs" :key="graph.id" :value="graph.name">
        {{ graph.name }}
      </option>
    </select>

    <!-- src/components/ButtonControls.vue -->
    <input
      type="date"
      v-model="graphStore.startDate"
      class="input-date"
      placeholder="Start Date"
    />
    <input
      type="date"
      v-model="graphStore.endDate"
      class="input-date"
      placeholder="End Date"
    />

    <select v-model="graphStore.timeframe" class="select-timeframe">
      <option value="1min">1 Min</option>
      <option value="5min">5 Min</option>
      <option value="15min">15 Min</option>
      <option value="30min">30 Min</option>
    </select>

    <select v-model="graphStore.symbol" class="select-symbol">
      <option disabled value="">Select a symbol</option>
      <option v-for="symbol in graphStore.symbolOptions" :key="symbol" :value="symbol">
        {{ symbol }}
      </option>
    </select>

    <button
      @click="async () => {
        await graphStore.saveGraphToServer();
        graphStore.compileGraph();
      }"
    >
      Compile
    </button>
    <button @click="graphStore.downloadGraph">Download</button>
    <button @click="triggerFileUpload">Upload</button>
    <input type="file" ref="fileInput" @change="handleFileUpload" accept=".json" style="display: none" />
  </div>
</template>

<script setup>
import { useGraphStore } from '../../stores/graph.ts'
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../../stores/auth.ts'

const graphStore = useGraphStore()
const fileInput = ref(null)
const authStore = useAuthStore()

onMounted(async () => {
  if (!authStore.isAuthenticated) {
    return
  }
})
const handleGraphChange = () => {
  graphStore.loadGraphFromServer()
  graphStore.graphName = graphStore.selectedGraph
}

const triggerFileUpload = () => {
  fileInput.value.click()
}

const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    const reader = new FileReader()
    reader.onload = (e) => {
      const contents = e.target.result
      try {
        const graphData = JSON.parse(contents)
        graphStore.loadGraphFromFile(graphData)
      } catch (error) {
        console.error('Error parsing uploaded graph JSON:', error)
      }
    }
    reader.readAsText(file)
  }
}
</script>
<style scoped>
.button-container{
  margin-top: 1vh;
  margin-bottom: 1vh;
}

</style>

<template>
  <div class="graph-container">
    <canvas ref="canvas"></canvas>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useGraphStore } from '../stores/graph.ts'

const canvas = ref(null)
const graphStore = useGraphStore()

const handleResize = () => {
  graphStore.resizeCanvas()
}

onMounted(() => {
  graphStore.initializeGraph(canvas.value)
  graphStore.populateSymbolDropdown()
  graphStore.setDefaultDates()
  graphStore.fetchSavedGraphs()
  handleResize()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (graphStore.graph) {
    graphStore.graph.stop()
  }
})
</script>

<style scoped>
.graph-container {
  width: 100%;
  height: 100%;
}
</style>

<template>
  <div class="graph-container" v-if="authStore.isAuthenticated">
    <canvas ref="canvas"></canvas>
  </div>
  <div v-else class="unauthorized">
    <p>You must be logged in to view this page.</p>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useGraphStore } from '../../stores/graph.ts'
import { useAuthStore } from '../../stores/auth.ts'
import { toast } from 'vue3-toastify'
const pve = { position: toast.POSITION.BOTTOM_RIGHT };
const canvas = ref(null)
const graphStore = useGraphStore()
const authStore = useAuthStore()

const handleResize = () => {
  graphStore.resizeCanvas()
}

onMounted(async () => {
  if (!authStore.isAuthenticated) {
    return
  }

  graphStore.initializeGraph(canvas.value)
  graphStore.populateSymbolDropdown()
  graphStore.setDefaultDates()
  handleResize()
  await graphStore.fetchSavedGraphs()

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
  min-height: 800px;
}

.unauthorized {
  text-align: center;
  padding: 20px;
  font-size: 18px;
  color: red;
}
</style>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { LGraph, LGraphCanvas, LiteGraph } from 'litegraph.js'

defineProps({
  msg: String,
})

const count = ref(0)
let graph
let canvas
let graphCanvas

const resizeCanvas = () => {
  const canvasElement = document.getElementById('mycanvas')
  if (canvasElement) {
    canvasElement.width = window.innerWidth
    canvasElement.height = window.innerHeight
    if (graphCanvas) {
      graphCanvas.resize()  // Update the LGraphCanvas size
    }
  }
}

const exportGraphToJson = () => {
  const json = graph.serialize()
  const jsonString = JSON.stringify(json, null, 2)
  console.log(jsonString)  // For demonstration, log it to the console. You could also save this to a file or server.
}

const loadGraphFromJson = (json) => {
  graph.clear()  // Clear the current graph
  graph.configure(json)  // Load the graph from the JSON object
}

onMounted(() => {
  resizeCanvas()  // Set initial canvas size

  graph = new LGraph()
  graphCanvas = new LGraphCanvas("#mycanvas", graph)

  const node_const = LiteGraph.createNode("basic/const")
  node_const.pos = [200, 200]
  graph.add(node_const)
  node_const.setValue(4.5)

  const node_watch = LiteGraph.createNode("basic/watch")
  node_watch.pos = [700, 200]
  graph.add(node_watch)

  node_const.connect(0, node_watch, 0)

  graph.start()

  window.addEventListener('resize', resizeCanvas)  // Listen to window resize

  // Example of exporting the graph to JSON
  exportGraphToJson()

  // Example of loading a graph from JSON (after the graph has been created)
  // const exampleJson = {"last_node_id":3,"nodes":[...],"links":[...]}
  // loadGraphFromJson(exampleJson)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCanvas)  // Clean up the event listener
})
</script>

<template>
  <canvas id='mycanvas' style='border: 1px solid'></canvas>
</template>

<style scoped>
.read-the-docs {
  color: #888;
}
</style>

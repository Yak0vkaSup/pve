<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { LGraph, LGraphCanvas, LiteGraph } from 'litegraph.js'
import { MyAddNode } from './custom_nodes/MyAddNode.js'  // Import the custom node

defineProps({
  msg: String,
})

const count = ref(0)
let graph
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
  console.log(jsonString)  // Log it to the console
}

const loadGraphFromJson = (json) => {
  graph.clear()  // Clear the current graph
  graph.configure(json)  // Load the graph from the JSON object
}

onMounted(() => {
  resizeCanvas()  // Set initial canvas size

  graph = new LGraph()
  graphCanvas = new LGraphCanvas("#mycanvas", graph)

  // Create constant node
  const node_const = LiteGraph.createNode("basic/const")
  node_const.pos = [200, 200]
  graph.add(node_const)
  node_const.setValue(4.5)

  // Create watch node
  const node_watch = LiteGraph.createNode("basic/watch")
  node_watch.pos = [700, 200]
  graph.add(node_watch)

  // Create sum node from the custom node
  const node_sum = LiteGraph.createNode("basic/sum");
  node_sum.pos = [400, 200];  // Position the sum node
  graph.add(node_sum);

  // Connect constant node to sum node
  node_const.connect(0, node_sum, 0);

  // Connect sum node to watch node
  node_sum.connect(0, node_watch, 0);

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
  <canvas id='mycanvas'></canvas>
</template>

<style scoped>
canvas {
  width: 100%;
  height: 100%;
  border: 1px solid black;
}
</style>

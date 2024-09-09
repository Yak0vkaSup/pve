<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { LGraph, LGraphCanvas, LiteGraph } from 'litegraph.js'
import { FetchDataNode } from './custom_nodes/GetDataNode.js'  // Import the custom FetchDataNode
import { MyAddNode } from './custom_nodes/MyAddNode.js'
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
  // const node_const = LiteGraph.createNode("basic/const")
  // node_const.pos = [200, 200]
  // graph.add(node_const)
  // node_const.setValue(4.5)

  // // Create watch node
  // const node_watch = LiteGraph.createNode("basic/watch")
  // node_watch.pos = [700, 200]
  // graph.add(node_watch)

  // // Create and add FetchDataNode to the graph
  const node_data = LiteGraph.createNode("basic/sum");
  // node_data.pos = [800, 500];  // Position the fetch data node
  // graph.add(node_data);

  // Connect the nodes

  // You can connect fetch data node's output to other nodes if needed
  // For example: node_data.connect(0, node_watch, 0);

  graph.start()  // Start the graph

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

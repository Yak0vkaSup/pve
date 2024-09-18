<template>
  <div class="graph-container">
    <canvas id="mycanvas"></canvas>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { LGraph, LGraphCanvas, LiteGraph } from 'litegraph.js'
import 'litegraph.js/css/litegraph.css'

// Import your custom nodes
import './custom_nodes/FetchDataNode.js'
import './custom_nodes/VisualizeDataNode.js'

const graph = ref(null)
const graphCanvas = ref(null)

const resizeCanvas = () => {
  const canvasElement = document.getElementById('mycanvas')
  if (canvasElement) {
    const parentElement = canvasElement.parentElement
    if (parentElement) {
      canvasElement.width = parentElement.clientWidth
      canvasElement.height = parentElement.clientHeight
    }
    if (graphCanvas.value) {
      graphCanvas.value.resize()
    }
  }
}

onMounted(() => {
  resizeCanvas()

  // Initialize the graph and canvas
  graph.value = new LGraph()
  graphCanvas.value = new LGraphCanvas('#mycanvas', graph.value)

  // Create FetchDataNode
  const fetchDataNode = LiteGraph.createNode('custom/fetch')
  fetchDataNode.pos = [200, 200]
  graph.value.add(fetchDataNode)

  // Create VisualizeDataNode
  const visualizeNode = LiteGraph.createNode('custom/vizualize')
  visualizeNode.pos = [600, 200]
  graph.value.add(visualizeNode)

  // Connect the nodes
  fetchDataNode.connect(0, visualizeNode, 0)

  // Start the graph
  graph.value.start()

  // Remove or comment out the onExecute function
  // visualizeNode.onExecute = function () {
  //   console.log("Event 'visualize_node_button_clicked' triggered");
  //   sendGraphToServer();
  // };

  window.addEventListener('resize', resizeCanvas)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCanvas)
  if (graph.value) {
    graph.value.stop()
  }
})

// Function to serialize the graph and send it to the Flask API
function sendGraphToServer() {
  const serializedGraph = graph.value.serialize()
  console.log('Graph JSON:', JSON.stringify(serializedGraph, null, 2))

  // Send the JSON to the Flask API
  fetch('https://pve.finance/api/receive-graph', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(serializedGraph)
  })
    .then((response) => response.json())
    .then((data) => {
      console.log('Response from server:', data)
    })
    .catch((error) => {
      console.error('Error sending graph to server:', error)
    })
}
</script>

<style scoped>
.graph-container {
  width: 100%;
  height: 100%;
}

canvas {
  width: 100%;
  height: 100%;
  border: 1px solid black;
}
</style>

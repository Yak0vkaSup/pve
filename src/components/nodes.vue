<template>
  <div class="button-container">
    <input v-model="graphName" placeholder="Enter graph name" />

    <button @click="saveGraphToServer">Save Graph</button>

    <select
      v-model="selectedGraph"
      @focus="fetchSavedGraphs"
      @change="
        () => {
          loadGraphFromServer()
          updateGraphName()
        }
      "
    >
      <option disabled value="">Select a saved graph</option>
      <option v-for="graph in savedGraphs" :key="graph.id" :value="graph.name">
        {{ graph.name }}
      </option>
    </select>

    <button @click="compileGraph">Compile</button>
  </div>
  <div class="graph-container">
    <canvas id="mycanvas"></canvas>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { LGraph, LGraphCanvas, LiteGraph } from 'litegraph.js'
import 'litegraph.js/css/litegraph.css'

// Import your custom nodes
import './custom_nodes/VisualizeDataNode.js'
import './custom_nodes/GetAllIndicatorsNode.js'
import './custom_nodes/GetDataFromDbNode.js'
import './custom_nodes/MultiplyColumnNode.js'
import './custom_nodes/indicators/RSINode.js'
import './custom_nodes/indicators/BollingerNode.js'
import './custom_nodes/indicators/MaNode.js'

const graph = ref(null)
const graphCanvas = ref(null)
const graphName = ref('')
const savedGraphs = ref([])
const selectedGraph = ref('')

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

  // Create VisualizeDataNode
  const visualizeNode = LiteGraph.createNode('custom/vizualize')
  visualizeNode.pos = [900, 200]
  graph.value.add(visualizeNode)

  // Create GetDataFromDbNode
  const getdataNode = LiteGraph.createNode('custom/data/get')
  getdataNode.pos = [600, 200]
  graph.value.add(getdataNode)

  // Create GetAllIndicatorsNode
  const getAllIndicatorsNode = LiteGraph.createNode('custom/data/indicatorslist')
  getAllIndicatorsNode.pos = [900, 200]
  graph.value.add(getAllIndicatorsNode)

  // Create MultiplityColumnNode
  const multiplycolumnNode = LiteGraph.createNode('custom/data/multiplycolumn')
  multiplycolumnNode.pos = [1200, 200]
  graph.value.add(multiplycolumnNode)

  // Create RSINode
  const RSINode = LiteGraph.createNode('custom/indicators/rsi')
  RSINode.pos = [1200, 200]
  graph.value.add(RSINode)

  // Create BollingerNode
  const bollingerNode = LiteGraph.createNode('custom/indicators/bollinger')
  bollingerNode.pos = [1200, 400]
  graph.value.add(bollingerNode)

  // Create MaNode
  const maNode = LiteGraph.createNode('custom/indicators/ma')
  maNode.pos = [1200, 600]
  graph.value.add(maNode)


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

function compileGraph() {
  const userId = localStorage.getItem('userId')
  const userToken = localStorage.getItem('userToken')

  if (!selectedGraph.value) {
    alert('Please select a graph to compile')
    return
  }

  const requestData = {
    user_id: userId,
    token: userToken,
    name: selectedGraph.value // Send the selected graph name
  }

  // Send the request to the backend
  fetch('https://pve.finance/api/compile-graph', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(requestData)
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status === 'success') {
        alert('Graph compiled successfully.')
      } else {
        alert(`Error compiling graph: ${data.message}`)
      }
    })
    .catch((error) => {
      console.error('Error compiling graph:', error)
    })
}
function fetchSavedGraphs() {
  const userId = localStorage.getItem('userId')
  const userToken = localStorage.getItem('userToken')

  fetch(`https://pve.finance/api/get-saved-graphs?user_id=${userId}&token=${userToken}`)
    .then((response) => response.json())
    .then((data) => {
      if (data.status === 'success') {
        savedGraphs.value = data.graphs // Store the saved graphs in the dropdown
      } else {
        console.error('Error fetching saved graphs:', data.message)
      }
    })
    .catch((error) => {
      console.error('Error fetching saved graphs:', error)
    })
}

// Function to load a graph from the server
function loadGraphFromServer() {
  const userId = localStorage.getItem('userId')
  const userToken = localStorage.getItem('userToken')

  if (!selectedGraph.value) {
    alert('Please select a graph to load')
    return
  }

  const requestData = {
    user_id: userId,
    token: userToken,
    name: selectedGraph.value // Send the selected graph name
  }

  fetch('https://pve.finance/api/load-graph', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(requestData)
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status === 'success') {
        // Deserialize the graph
        graph.value.clear() // Clear the existing graph
        graph.value.configure(data.graph_data) // Load the new graph
        graph.value.start()
      } else {
        console.error('Error loading graph:', data.message)
      }
    })
    .catch((error) => {
      console.error('Error loading graph:', error)
    })
}

function updateGraphName() {
  graphName.value = selectedGraph.value // Set the graph name to the selected graph name
}

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCanvas)
  if (graph.value) {
    graph.value.stop()
  }
})

// Function to save or update the graph on the server
function saveGraphToServer() {
  const serializedGraph = graph.value.serialize() // Serialize the graph
  const userId = localStorage.getItem('userId') // Get user ID from local storage
  const userToken = localStorage.getItem('userToken') // Get user token from local storage

  if (!graphName.value) {
    alert('Please enter a graph name.')
    return
  }

  const requestData = {
    user_id: userId,
    token: userToken,
    name: graphName.value, // Send the graph name
    graph_data: serializedGraph // Send the serialized graph data
  }

  // Send the request to the backend
  fetch('https://pve.finance/api/save-graph', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(requestData)
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status === 'success') {
        alert('Graph saved successfully.')
        fetchSavedGraphs() // Refresh saved graphs list after saving
      } else {
        alert(`Error: ${data.message}`)
      }
    })
    .catch((error) => {
      console.error('Error saving graph:', error)
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

.button-container {
  display: flex;
  justify-content: flex-start;
  gap: 10px;
  margin-bottom: 8px;
}

button,
input,
select {
  padding: 10px 20px;
  background-color: #222222; /* Same background color as buttons */
  color: white; /* White text color for contrast */
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s ease;
  margin-bottom: 0px; /* Space below the element */
  margin-right: 10px; /* Space to the right of the element */
}

input,
select {
  width: auto; /* Set width automatically based on content, similar to button size */
}

button:hover,
input:hover,
select:hover {
  background-color: #353535; /* Darker grey when hovered */
}

input::placeholder {
  color: white; /* Placeholder text color */
}
</style>

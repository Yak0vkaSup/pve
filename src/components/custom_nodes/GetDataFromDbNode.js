// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetDataFromDbNode() {
  // this.addInput('Data', 'number')
  this.addOutput ("DFo", "number"),("DFh", "number"),("DFl", "number"),("DFc", "number"),("DFv", "number")
  this.properties = { 
    precision: 1,
    symbol: "TONUSDT",
    startDate: "DD/MM/YYYY",
    endDate: "DD/MM/YYYY",
   };
  // Add a button widget to the node
  this.addWidget('button', 'Get data', null, () => {
    // When the button is clicked, trigger an event
    this.sendGraphToServer()
  })

  // Define sendGraphToServer as a method of the node
  this.sendGraphToServer = function () {
    if (this.graph) {
      const serializedGraph = this.graph.serialize()
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
    } else {
      console.error('Graph is not defined in the node.')
    }
  }
}

// Set the title for the node
GetDataFromDbNode.title = 'Get data From DB'

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/data/get', GetDataFromDbNode)

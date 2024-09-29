// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function VizualizeData() {
  this.addInput('Data', 'number')
  this.properties = { precision: 1 }

  // Add a button widget to the node
  this.addWidget('button', 'Update Chart', null, () => {
    // When the button is clicked, trigger an event
    this.sendGraphToServer()
  })
}

// Set the title for the node
VizualizeData.title = 'Vizualize Data'

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/vizualize', VizualizeData)

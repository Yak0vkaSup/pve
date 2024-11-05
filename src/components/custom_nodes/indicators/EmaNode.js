// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function EmaNode() {
  // this.addInput('Data', 'number')
  this.addInput('Column', 'column')
  this.addInput('Window', 'integer')

  this.addOutput('EMA', 'column')

  this.serialize_widgets = true
}

// Set the title for the node
EmaNode.title = 'EMA'

// Register the node with LiteGraph
LiteGraph.registerNodeType('indicators/ema', EmaNode)

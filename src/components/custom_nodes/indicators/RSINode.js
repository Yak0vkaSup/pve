// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function RSINode() {
  this.addInput('Float', 'float')
  this.addInput('Length', 'integer')

  this.addOutput('Float', 'float')

  this.serialize_widgets = true
}

// Set the title for the node
RSINode.title = 'RSI'

// Register the node with LiteGraph
LiteGraph.registerNodeType('indicators/rsi', RSINode)

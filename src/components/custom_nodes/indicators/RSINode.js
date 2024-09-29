// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function RSINode() {
  // this.addInput('Data', 'number')
  this.addInput ("Close","dataframe")
  this.addOutput ("rsi", "dataframe");

  this.properties = { 
    windows : 7,
   };
}

// Set the title for the node
RSINode.title = 'RSI'

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/indicators/rsi', RSINode)

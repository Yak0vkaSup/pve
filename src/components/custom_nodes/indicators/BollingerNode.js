// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function BollingerNode() {
  // this.addInput('Data', 'number')
  this.addInput ("Close","dataframe")
  this.addOutput ("Lower", "dataframe");
  this.addOutput ("Mid", "dataframe");
  this.addOutput ("Upper", "dataframe");

  this.properties = { 
    windows : 7,
   };
}

// Set the title for the node
BollingerNode.title = 'Bollinger'

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/indicators/bollinger', BollingerNode)

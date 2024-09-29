// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function BollingerNode() {
  // this.addInput('Data', 'number')
  this.addInput ("Df","dataframe")
  this.addOutput ("Df Lower", "dataframe");
  this.addOutput ("Df Mid", "dataframe");
  this.addOutput ("Df Upper", "dataframe");

  this.properties = { 
    windows : 7,
   };
}

// Set the title for the node
BollingerNode.title = 'Bollinger'

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/indicators/bollinger', BollingerNode)

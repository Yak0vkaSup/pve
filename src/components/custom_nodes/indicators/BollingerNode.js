// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function BollingerNode() {
  this.addInput('Close', 'column')
  this.addInput('Window', 'int')

  this.addOutput ("Lower", "column");
  this.addOutput ("Mid", "column");
  this.addOutput ("Upper", "column");
  this.addOutput ("Bandwidth", "column");
  this.addOutput ("Percent", "column");

  this.serialize_widgets = true;
}

// Set the title for the node
BollingerNode.title = 'Bollinger'

// Register the node with LiteGraph
LiteGraph.registerNodeType('indicators/bollinger', BollingerNode)

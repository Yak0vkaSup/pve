// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function MultiplyColumnNode() {
  // this.addInput('Data', 'number')
  this.addInput ('Input','column')
  this.addOutput ('Result', 'column');

  this.properties = { 
    factor : 0.9,
   };
  this.addWidget(
    "number",
    "Factor",
    this.properties.factor,
    (value) => {
      this.properties.factor = value;
    }
  );

  this.serialize_widgets = true
}

// Set the title for the node
MultiplyColumnNode.title = 'Multiply'

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/data/multiply', MultiplyColumnNode)

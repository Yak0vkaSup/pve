// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function MultiplyColumnNode() {
  // this.addInput('Data', 'number')
  this.addInput ("Df","dataframe")
  this.addOutput ("Df", "dataframe");

  this.properties = { 
    factor : 1,
   };
}

// Set the title for the node
MultiplyColumnNode.title = 'Multiply column'

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/data/multiplycolumnnode', MultiplyColumnNode)

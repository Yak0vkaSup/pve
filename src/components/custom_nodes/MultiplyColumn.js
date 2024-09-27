// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function MultiplyColumn() {
  // this.addInput('Data', 'number')
  this.addInput ("Df","dataframe")
  this.addOutput ("Df", "dataframe");

  this.properties = { 
    integer : 1,
   };
}

// Set the title for the node
MultiplyColumn.title = 'Multiply column on integer'

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/data/multiplycolumn', MultiplyColumn)

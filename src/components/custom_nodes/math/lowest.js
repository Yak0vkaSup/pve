// Import LiteGraph
import { LiteGraph } from 'litegraph.js';

export function LowestNode() {
  this.addInput('Float', 'float');
  this.addInput('Length', 'integer');

  // Initialize default properties
  this.properties = {};

  this.addOutput('Float', 'float');

  this.serialize_widgets = true;
}

// Set the title for the node
LowestNode.title = 'Lowest';

// Register the node with LiteGraph
LiteGraph.registerNodeType('math/lowest', LowestNode); 
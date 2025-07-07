// Import LiteGraph
import { LiteGraph } from 'litegraph.js';

export function HighestNode() {
  this.addInput('Float', 'float');
  this.addInput('Length', 'integer');

  // Initialize default properties
  this.properties = {};

  this.addOutput('Float', 'float');

  this.serialize_widgets = true;
}

// Set the title for the node
HighestNode.title = 'Highest';

// Register the node with LiteGraph
LiteGraph.registerNodeType('math/highest', HighestNode); 
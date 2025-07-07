// Import LiteGraph
import { LiteGraph } from 'litegraph.js';

export function TrueRangeNode() {
  this.addInput('High', 'column');
  this.addInput('Low', 'column');
  this.addInput('Close', 'column');

  this.addOutput('TrueRange', 'column');

  this.serialize_widgets = true;
}

// Set the title for the node
TrueRangeNode.title = 'TrueRange';

// Register the node with LiteGraph
LiteGraph.registerNodeType('indicators/true_range', TrueRangeNode);

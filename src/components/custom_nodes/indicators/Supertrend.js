// Import LiteGraph
import { LiteGraph } from 'litegraph.js';

export function SuperTrendNode() {
  // Inputs
  this.addInput('High', 'column');
  this.addInput('Low', 'column');
  this.addInput('Close', 'column');
  this.addInput('Window', 'integer');

  // Outputs
  this.addOutput('Trend', 'column');
  this.addOutput('Direction', 'column');
  this.addOutput('Long', 'column');
  this.addOutput('Short', 'column');

  this.serialize_widgets = true;
}

// Set the title for the node
SuperTrendNode.title = 'SuperTrend';

// Register the node with LiteGraph
LiteGraph.registerNodeType('indicators/super_trend', SuperTrendNode);

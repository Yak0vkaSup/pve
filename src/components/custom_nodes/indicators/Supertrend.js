// Import LiteGraph
import { LiteGraph } from 'litegraph.js';

export function SuperTrendNode() {
  // Inputs
  this.addInput('High', 'float');
  this.addInput('Low', 'float');
  this.addInput('Close', 'float');
  this.addInput('Length', 'integer');

  // Add a multiplier widget
  this.addWidget('number', 'Multiplier', 3.0, (value) => {
    this.properties.multiplier = value;
  }, { min: 0.1, max: 10.0, step: 0.1 });

  // Initialize default properties
  this.properties = { multiplier: 3.0 };

  // Output
  this.addOutput('Float', 'float');

  this.serialize_widgets = true;
}

// Set the title for the node
SuperTrendNode.title = 'SuperTrend';

// Register the node with LiteGraph
LiteGraph.registerNodeType('indicators/super_trend', SuperTrendNode);

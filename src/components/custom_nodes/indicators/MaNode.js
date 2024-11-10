// Import LiteGraph
import { LiteGraph } from 'litegraph.js';

export function MaNode() {
  this.addInput('Column', 'column');
  this.addInput('Length', 'integer');

  // Add a dropdown widget to select the MA type
  this.addWidget('combo', 'MA Type', 'ema', (value) => {
    this.properties.ma_type = value;
  }, { values: ['dema', 'ema', 'fwma', 'hma', 'linreg', 'midpoint', 'pwma', 'rma', 'sinwma', 'sma', 'swma', 't3', 'tema', 'trima', 'vidya', 'wma', 'zlma'] });

  // Initialize default properties
  this.properties = { ma_type: 'ema'};

  this.addOutput('MA', 'column');
  this.addOutput('Default name', 'string');

  this.serialize_widgets = true;
}

// Set the title for the node
MaNode.title = 'MA';

// Register the node with LiteGraph
LiteGraph.registerNodeType('indicators/ma', MaNode);

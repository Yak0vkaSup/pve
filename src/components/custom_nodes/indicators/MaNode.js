// Import LiteGraph
import { LiteGraph } from 'litegraph.js';

export function MaNode() {
  this.addInput('Float', 'float');
  this.addInput('Length', 'integer');

  // Add a dropdown widget to select the MA type - only single-input single-output MAs
  this.addWidget('combo', 'MA Type', 'ema', (value) => {
    this.properties.ma_type = value;
  }, { 
    values: [
      'alma',         // Arnaud Legoux Moving Average
      'dema',         // Double Exponential Moving Average
      'ema',          // Exponential Moving Average
      'fwma',         // Fibonacci's Weighted Moving Average
      'hma',          // Hull Moving Average
      'hwma',         // Holt-Winter Moving Average
      'jma',          // Jurik Moving Average
      'kama',         // Kaufman's Adaptive Moving Average
      'linreg',       // Linear Regression Moving Average
      'mcgd',         // McGinley Dynamic Indicator
      'pwma',         // Pascal's Weighted Moving Average
      'rma',          // wildeR's Moving Average
      'sinwma',       // Sine Weighted Moving Average
      'sma',          // Simple Moving Average
      'smma',         // SMoothed Moving Average
      'ssf',          // Ehlers's Super Smoother Filter
      'ssf3',         // Ehlers's 3 Pole Super Smoother Filter
      'swma',         // Symmetric Weighted Moving Average
      't3',           // T3
      'tema',         // Triple Exponential Moving Average
      'trima',        // Triangular Moving Average
      'vidya',        // Variable Index Dynamic Average
      'wma',          // Weighted Moving Average
      'zlma'          // Zero Lag Moving Average
    ] 
  });

  // Initialize default properties
  this.properties = { ma_type: 'ema'};

  this.addOutput('Float', 'float');

  this.serialize_widgets = true;
}

// Set the title for the node
MaNode.title = 'MA';

// Register the node with LiteGraph
LiteGraph.registerNodeType('indicators/ma', MaNode);

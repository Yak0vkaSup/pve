// src/custom_nodes/MyAddNode.js

// Import LiteGraph so it's available in this file
import { LiteGraph } from 'litegraph.js';

export function MyAddNode() {
  this.addInput("A", "number");
  this.addInput("B", "number");
  this.addOutput("A+B", "number");
  this.properties = { precision: 1 };
}

// Set the title for the node
MyAddNode.title = "Data";

// Execution logic for the node
MyAddNode.prototype.onExecute = function () {
  const A = this.getInputData(0) || 0;
  const B = this.getInputData(1) || 0;
  this.setOutputData(0, A + B);
}

// Register the node with LiteGraph
LiteGraph.registerNodeType("custom/pve", MyAddNode);

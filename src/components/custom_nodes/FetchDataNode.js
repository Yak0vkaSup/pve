// Import LiteGraph so it's available in this file
import { LiteGraph } from 'litegraph.js';

export function FetchData() {
  this.addOutput("Data", "number");
  this.properties = { 
    precision: 1,
    symbol: "TONUSDT",
   };
}

// Set the title for the node
FetchData.title = "Fetch Data";


// Register the node with LiteGraph
LiteGraph.registerNodeType("custom/fetch", FetchData);

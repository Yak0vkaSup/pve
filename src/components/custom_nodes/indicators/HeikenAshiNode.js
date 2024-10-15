import { LiteGraph } from 'litegraph.js';

export function HeikinAshiNode() {
    // Initialize the base node with four fixed inputs
    this.addInput('Open', 'column');
    this.addInput('High', 'column');
    this.addInput('Low', 'column');
    this.addInput('Close', 'column');

    // Initialize four outputs for Heikin Ashi OHLC
    this.addOutput('HA_Open', 'column');
    this.addOutput('HA_High', 'column');
    this.addOutput('HA_Low', 'column');
    this.addOutput('HA_Close', 'column');

    // No properties required, set node size and appearance
    this.size = [200, 100];
    this.title = "Heikin Ashi";

    // Ensure widgets are serialized with the node
    this.serialize_widgets = true;
}

// Define the node's title and description
HeikinAshiNode.title = "Heikin Ashi";
HeikinAshiNode.desc = "Calculates Heikin Ashi OHLC values";

// Register the node with LiteGraph
LiteGraph.registerNodeType("custom/indicators/heikin_ashi", HeikinAshiNode);

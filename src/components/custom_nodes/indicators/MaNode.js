// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function MaNode() {
  // this.addInput('Data', 'number')
  this.addInput ("Close","dataframe")
  this.addOutput ("ma", "dataframe");

  this.properties = { 
    windows : 7,
   };

   this.addWidget(
    'combo',
    'Precision',
    this.properties.precision,
    (value) => {
      this.properties.precision = value
    },
    { values: ["dma", "ema", "hma", "rma", "sinwma", "sma", "swma", "tema", "trima","wma","zlma"] }
  );
  this.serialiaz_widgets = true

}


// Set the title for the node
MaNode.title = 'MA'

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/indicators/ma', MaNode)

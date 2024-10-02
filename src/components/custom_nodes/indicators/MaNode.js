// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function MaNode() {
  // this.addInput('Data', 'number')
  this.addInput('Close', 'column')
  this.addOutput('MA', 'column')

<<<<<<< HEAD
  this.properties = { 
    Window : 7,
    Mode : 'ema'
   };
=======
  this.properties = {
    windows: 7,
    mode: 'ema'
  }
>>>>>>> yakov

  this.addWidget(
    'combo',
<<<<<<< HEAD
    'Mode',
    this.properties.Mode,
    (value) => {
      this.properties.Mode = value
=======
    'mode',
    this.properties.mode,
    (value) => {
      this.properties.mode = value
>>>>>>> yakov
    },
    {
      values: ['dma', 'ema', 'hma', 'rma', 'sinwma', 'sma', 'swma', 'tema', 'trima', 'wma', 'zlma']
    }
  )
  this.serialiaz_widgets = true
}

// Set the title for the node
MaNode.title = 'MA'

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/indicators/ma', MaNode)

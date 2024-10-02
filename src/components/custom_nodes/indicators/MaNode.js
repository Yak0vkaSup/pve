// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function MaNode() {
  // this.addInput('Data', 'number')
  this.addInput('Close', 'column')
  this.addOutput('MA', 'column')

  this.properties = {
    windows: 7,
    mode: 'ema'
  }

  this.addWidget(
    'combo',
    'mode',
    this.properties.mode,
    (value) => {
      this.properties.mode = value
    },
    {
      values: ['dma', 'ema', 'hma', 'rma', 'sinwma', 'sma', 'swma', 'tema', 'trima', 'wma', 'zlma']
    }
  )
  this.serialize_widgets = true
}

// Set the title for the node
MaNode.title = 'MA'

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/indicators/ma', MaNode)

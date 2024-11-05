// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function MaNode() {
  // this.addInput('Data', 'number')
  this.addInput('Column', 'column')
  this.addInput('Window', 'integer')
  this.addInput('Name', 'column')

  this.addOutput('Result', 'column')

  this.properties = {
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
LiteGraph.registerNodeType('indicators/ma', MaNode)

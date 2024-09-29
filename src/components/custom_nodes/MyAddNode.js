// Import LiteGraph so it's available in this file
import { LiteGraph } from 'litegraph.js'

export function MyAddNode() {
  this.addInput('A', 'number')
  this.addInput('B', 'number')
  this.addOutput('A+B', 'number')
  this.properties = { precision: 1 }

  // Add a dropdown widget for precision property
  this.addWidget(
    'combo',
    'Precision',
    this.properties.precision,
    (value) => {
      this.properties.precision = value
    },
    { values: [1, 2, 3, 4, 5, 6, 7, 8, 9] }
  )
  this.serialize_widgets = true
}

// Set the title for the node
MyAddNode.title = 'Data'

// Execution logic for the node
MyAddNode.prototype.onExecute = function () {
  const A = this.getInputData(0) || 0
  const B = this.getInputData(1) || 0
  // Use the precision property to set the precision of the output
  const result = parseFloat((A + B).toFixed(this.properties.precision))
  this.setOutputData(0, result)
}

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/pve', MyAddNode)

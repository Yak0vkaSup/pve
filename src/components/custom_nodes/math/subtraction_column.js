// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function SubtractionColumnNode() {
  this.addInput('Column', 'column')
  this.addInput('Column', 'column')
  this.addOutput('Result', 'column')
  this.serialize_widgets = true
}

SubtractionColumnNode.title = 'Subtract column'

LiteGraph.registerNodeType('math/subtraction_column', SubtractionColumnNode)

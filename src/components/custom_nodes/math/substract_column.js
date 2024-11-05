// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function SubtractColumnNode() {
  this.addInput('Column', 'column')
  this.addInput('Column', 'column')
  this.addOutput('Result', 'column')
  this.serialize_widgets = true
}

SubtractColumnNode.title = 'Subtract column'

LiteGraph.registerNodeType('math/subtract_column', SubtractColumnNode)

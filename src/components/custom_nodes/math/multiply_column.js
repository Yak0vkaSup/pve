// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function MultiplyColumnNode() {
  this.addInput('Column', 'column')
  this.addInput('Coefficient', 'float')

  this.addOutput('Result', 'column')

  this.serialize_widgets = true
}

MultiplyColumnNode.title = 'Multiply column'

LiteGraph.registerNodeType('math/multiply_column', MultiplyColumnNode)

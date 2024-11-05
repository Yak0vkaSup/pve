// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function MultiplyColumnNode() {
  this.addInput('Column', 'column')
  this.addOutput('Result', 'column')
  this.addInput('Coefficient', 'float')
  this.serialize_widgets = true
}

MultiplyColumnNode.title = 'Multiply column'

LiteGraph.registerNodeType('math/multipy_column', MultiplyColumnNode)

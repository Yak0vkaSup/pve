// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function MultiplyFloatNode() {
  this.addInput('Float', 'float')
  this.addInput('Float', 'float')

  this.addOutput('Float', 'float')

  this.serialize_widgets = true
}

MultiplyFloatNode.title = 'Multiply Float'

LiteGraph.registerNodeType('math/multiply_float', MultiplyFloatNode)

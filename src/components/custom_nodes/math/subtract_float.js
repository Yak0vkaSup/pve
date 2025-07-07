// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function SubtractFloatNode() {
  this.addInput('Float', 'float')
  this.addInput('Float', 'float')

  this.addOutput('Float', 'float')

  this.serialize_widgets = true
}

SubtractFloatNode.title = 'Subtract Float'

LiteGraph.registerNodeType('math/subtract_float', SubtractFloatNode) 
// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function DivideFloatNode() {
  this.addInput('Float', 'float')
  this.addInput('Float', 'float')

  this.addOutput('Float', 'float')

  this.serialize_widgets = true
}

DivideFloatNode.title = 'Divide Float'

LiteGraph.registerNodeType('math/divide_float', DivideFloatNode)

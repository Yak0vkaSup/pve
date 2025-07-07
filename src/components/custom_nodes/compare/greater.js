// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GreaterNode() {
  this.addInput('Float', 'float')
  this.addInput('Float', 'float')

  this.addOutput('Bool', 'bool')

  this.serialize_widgets = true
}

GreaterNode.title = 'Greater'

LiteGraph.registerNodeType('compare/greater', GreaterNode)

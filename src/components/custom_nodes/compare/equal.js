// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function EqualNode() {
  this.addInput('Float', 'float')
  this.addInput('Float', 'float')

  this.addOutput('Bool', 'bool')

  this.serialize_widgets = true
}

EqualNode.title = 'Equal'

LiteGraph.registerNodeType('compare/equal', EqualNode)

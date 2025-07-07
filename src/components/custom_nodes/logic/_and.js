// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function AndNode() {
  this.addInput('Bool', 'bool')
  this.addInput('Bool', 'bool')

  this.addOutput('Bool', 'bool')

  this.serialize_widgets = true
}

AndNode.title = 'AND'

LiteGraph.registerNodeType('logic/and', AndNode)

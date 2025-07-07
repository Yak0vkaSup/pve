// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function OrNode() {
  this.addInput('Bool', 'bool')
  this.addInput('Bool', 'bool')

  this.addOutput('Bool', 'bool')

  this.serialize_widgets = true
}

OrNode.title = 'OR'

LiteGraph.registerNodeType('logic/or', OrNode)

// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function NotNode() {
  this.addInput('Bool', 'bool')

  this.addOutput('Bool', 'bool')

  this.serialize_widgets = true
}

NotNode.title = 'NOT'

LiteGraph.registerNodeType('logic/not', NotNode)

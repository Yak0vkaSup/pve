// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function IfNode() {
  this.addInput('Bool', 'bool')

  this.addOutput('True', 'exec')
  this.addOutput('False', 'exec')

  this.serialize_widgets = true
}

IfNode.title = 'IF'

LiteGraph.registerNodeType('logic/if', IfNode)

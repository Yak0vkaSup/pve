// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function IfNode() {
  this.addInput('Condition', 'boolean')

  this.addOutput('True', 'boolean')
  this.addOutput('False', 'boolean')

  this.serialize_widgets = true
}

IfNode.title = 'IF'

LiteGraph.registerNodeType('logic/if', IfNode)

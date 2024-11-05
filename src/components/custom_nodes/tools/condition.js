// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function IfNode() {
  this.addInput('Condition', 'boolean')

  this.addOutput('True', 'column')

  this.serialize_widgets = true
}

IfNode.title = 'Get column'

LiteGraph.registerNodeType('tools/if', IfNode)

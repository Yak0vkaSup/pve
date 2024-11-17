// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function NotNode() {
  this.addInput('Condition', 'boolean')

  this.addOutput('Condition', 'boolean')

  this.serialize_widgets = true
}

NotNode.title = 'NOT'

LiteGraph.registerNodeType('logic/not', NotNode)

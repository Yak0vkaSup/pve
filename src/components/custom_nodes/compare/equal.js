// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function EqualNode() {
  this.addInput('Column', 'column')
  this.addInput('Column', 'column')

  this.addOutput('Condition', 'boolean')

  this.serialize_widgets = true
}

EqualNode.title = 'Equal'

LiteGraph.registerNodeType('compare/equal', EqualNode)

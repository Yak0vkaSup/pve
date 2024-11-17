// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function SmallerNode() {
  this.addInput('Column', 'column')
  this.addInput('Column', 'column')

  this.addOutput('Condition', 'boolean')

  this.serialize_widgets = true
}

SmallerNode.title = 'Smaller'

LiteGraph.registerNodeType('compare/smaller', SmallerNode)

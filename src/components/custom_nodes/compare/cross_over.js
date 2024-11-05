// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function CrossOverNode() {
  this.addInput('Column', 'column')
  this.addInput('Column', 'column')

  this.addOutput('Condition', 'boolean')

  this.serialize_widgets = true
}

CrossOverNode.title = 'Cross Over'

LiteGraph.registerNodeType('compare/cross_over', CrossOverNode)

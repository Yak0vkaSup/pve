// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function CrossOverNode() {
  this.addInput('Float', 'float')
  this.addInput('Float', 'float')

  this.addOutput('Condition', 'bool')

  this.serialize_widgets = true
}

CrossOverNode.title = 'Cross Over'

LiteGraph.registerNodeType('compare/cross_over', CrossOverNode)

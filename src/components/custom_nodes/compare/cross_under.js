// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function CrossUnderNode() {
  this.addInput('Float', 'float')
  this.addInput('Float', 'float')

  this.addOutput('Condition', 'bool')

  this.serialize_widgets = true
}

CrossUnderNode.title = 'Cross Under'

LiteGraph.registerNodeType('compare/cross_under', CrossUnderNode)

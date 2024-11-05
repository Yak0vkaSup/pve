// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetLowNode() {
  this.addOutput('low', 'column')

  this.serialize_widgets = true
}

GetLowNode.title = 'Get low price'

LiteGraph.registerNodeType('get/low', GetLowNode)

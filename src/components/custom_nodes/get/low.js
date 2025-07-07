// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetLowNode() {
  this.addOutput('low', 'float')

  this.serialize_widgets = true
}

GetLowNode.title = 'Get low price'

LiteGraph.registerNodeType('get/low', GetLowNode)

// Import LiteGraph
import { LiteGraph } from 'litegraph.js'
LiteGraph.clearRegisteredTypes();

export function GetOpenNode() {
  this.addOutput('open', 'float')

  this.serialize_widgets = true
}

GetOpenNode.title = 'Get open price'

LiteGraph.registerNodeType('get/open', GetOpenNode)

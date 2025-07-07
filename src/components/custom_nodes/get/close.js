// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetCloseNode() {
  this.addOutput('close', 'float')

  this.serialize_widgets = true
}

GetCloseNode.title = 'Get close price'

LiteGraph.registerNodeType('get/close', GetCloseNode)

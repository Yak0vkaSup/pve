// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetHighNode() {
  this.addOutput('high', 'float')

  this.serialize_widgets = true
}

GetHighNode.title = 'Get high price'

LiteGraph.registerNodeType('get/high', GetHighNode)

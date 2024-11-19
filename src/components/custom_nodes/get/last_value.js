// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetLowNode() {

  this.addInput('Column', 'column')
  this.addOutput('Value', 'float')

  this.serialize_widgets = true
}

GetLowNode.title = 'Get last value'

LiteGraph.registerNodeType('get/last_value', GetLowNode)

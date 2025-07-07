// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetLastOrder() {
  this.addOutput('Exists?', 'bool')
  this.addOutput('ID', 'string')
  this.addOutput('Long/Short', 'bool')
  this.addOutput('Normal/Conditional', 'bool')
  this.addOutput('Cancelled', 'bool')
  this.serialize_widgets = true
}

GetLastOrder.title = 'Get Last Order'

LiteGraph.registerNodeType('trade/get_last_order', GetLastOrder)

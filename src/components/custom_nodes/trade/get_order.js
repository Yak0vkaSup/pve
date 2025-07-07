// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetOrder() {
  this.addInput('ID', 'string')
  this.addOutput('ID', 'string')
  this.addOutput('Price', 'float')
  this.addOutput('Quantity', 'float')
  this.addOutput('Created', 'float')
  this.addOutput('Executed?', 'bool')
  this.addOutput('Open?', 'bool')
  this.serialize_widgets = true
}

GetOrder.title = 'Get Order'

LiteGraph.registerNodeType('trade/get_order', GetOrder)

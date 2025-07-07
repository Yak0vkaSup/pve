// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function SaveOrder() {
  this.addInput('Exec', 'exec')
  this.addInput('Order', 'object')
  this.addOutput('Exec', 'exec')
  this.addOutput('ID', 'string')


  this.serialize_widgets = true
}

SaveOrder.title = 'Save Order'

LiteGraph.registerNodeType('trade/save_order', SaveOrder)

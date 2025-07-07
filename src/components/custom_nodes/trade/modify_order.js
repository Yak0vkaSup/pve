// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function ModifyOrder() {
  this.addInput('Exec', 'exec')
  this.addInput('ID', 'string')
  this.addInput('Price', 'float')
  this.addInput('Quantity', 'float')
  this.addOutput('Exec', 'exec')
  this.addOutput('ID', 'string')

  this.serialize_widgets = true
}

ModifyOrder.title = 'ModifyOrder'

LiteGraph.registerNodeType('trade/modify_order', ModifyOrder)

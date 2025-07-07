// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function CancelOrder() {
  this.addInput('Exec', 'exec')
  this.addInput('ID', 'string')
  this.addOutput('Exec', 'exec')

  this.serialize_widgets = true
}

CancelOrder.title = 'Cancel Order'

LiteGraph.registerNodeType('trade/cancel_order', CancelOrder)

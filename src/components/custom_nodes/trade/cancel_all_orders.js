// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function CancelAllOrder() {
  this.addInput('Exec', 'exec')
  this.addOutput('Exec', 'exec')

  this.serialize_widgets = true
}

CancelAllOrder.title = 'Cancel All'

LiteGraph.registerNodeType('trade/cancel_all_order', CancelAllOrder)

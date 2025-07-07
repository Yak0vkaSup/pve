// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function CreateOrder() {
  this.addInput('Exec', 'exec')
  this.addInput('Long/Short', 'bool')
  this.addInput('Limit/Market', 'bool')
  this.addInput('Price', 'float')
  this.addInput('Quantity', 'float')
  this.addOutput('Exec', 'exec')
  this.addOutput('ID', 'string')
  this.properties = { description: "direction: true/false" +
                                    "type: true/false" };
  this.serialize_widgets = true
}

CreateOrder.title = 'Create Order'

LiteGraph.registerNodeType('trade/create_order', CreateOrder)

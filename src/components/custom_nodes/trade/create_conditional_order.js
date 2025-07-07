// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function CreateConditionalOrder() {
  this.addInput('Exec', 'exec')
  this.addInput('Long/Short', 'bool')
  this.addInput('Trigger Price', 'float')
  this.addInput('Quantity', 'float')
  this.addOutput('Exec', 'exec')
  this.addOutput('ID', 'string')
  this.properties = { description: "Always market order"};
  this.size = [200, 90]
  this.serialize_widgets = true
}

CreateConditionalOrder.title = 'Create Conditional Order'

LiteGraph.registerNodeType('trade/create_conditional_order', CreateConditionalOrder)

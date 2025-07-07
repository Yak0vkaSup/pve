// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetPosition() {
  this.addOutput('Price', 'float')
  this.addOutput('Quantity', 'float')
  this.addOutput('Created', 'integer')
  this.serialize_widgets = true
}

GetPosition.title = 'Get Position'

LiteGraph.registerNodeType('trade/get_position', GetPosition)

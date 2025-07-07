// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetShortPosition() {
  this.addOutput('Price', 'float')
  this.addOutput('Quantity', 'float')
  this.addOutput('Created', 'integer')
  this.serialize_widgets = true
}

GetShortPosition.title = 'Get Short Position'

LiteGraph.registerNodeType('trade/get_short_position', GetShortPosition)

// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetLongPosition() {
  this.addOutput('Price', 'float')
  this.addOutput('Quantity', 'float')
  this.addOutput('Created', 'integer')
  this.serialize_widgets = true
}

GetLongPosition.title = 'Get Long Position'

LiteGraph.registerNodeType('trade/get_long_position', GetLongPosition)

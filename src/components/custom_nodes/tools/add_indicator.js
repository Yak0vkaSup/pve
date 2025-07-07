// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function AddIndicatorNode() {
  this.addInput('Indicator', 'float')
  this.addInput('Name', 'string')

  this.serialize_widgets = true
}

AddIndicatorNode.title = 'Add Indicator'

LiteGraph.registerNodeType('tools/add_indicator', AddIndicatorNode)

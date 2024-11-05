// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetColumnNode() {
  this.addOutput('Column', 'column')
  this.addInput('Name', 'string')

  this.serialize_widgets = true
}

GetColumnNode.title = 'Get column'

LiteGraph.registerNodeType('tools/get_column', GetColumnNode)

// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function AddColumnNode() {
  this.addInput('Column', 'column')
  this.addInput('Name', 'string')


  this.serialize_widgets = true
}

AddColumnNode.title = 'Add column'

LiteGraph.registerNodeType('tools/add_column', AddColumnNode)

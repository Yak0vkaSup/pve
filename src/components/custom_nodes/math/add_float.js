// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function AddFloatNode() {
  this.addInput('Float', 'float')
  this.addInput('Float', 'float')

  this.addOutput('Float', 'float')

  this.serialize_widgets = true
}

AddFloatNode.title = 'Add Float'

LiteGraph.registerNodeType('math/add_float', AddFloatNode)

// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function AddSignalNode() {
  this.addInput('Signal', 'bool')
  this.addInput('Name', 'string')

  this.serialize_widgets = true
}

AddSignalNode.title = 'Add Signal'

LiteGraph.registerNodeType('tools/add_signal', AddSignalNode)

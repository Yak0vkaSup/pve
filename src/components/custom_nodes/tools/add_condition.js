// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function AddConditionNode() {
  this.addInput('Condition', 'boolean')
  this.addInput('Name', 'string')


  this.serialize_widgets = true
}

AddConditionNode.title = 'Add condition'

LiteGraph.registerNodeType('tools/add_condition', AddConditionNode)

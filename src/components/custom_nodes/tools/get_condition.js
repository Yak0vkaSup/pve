// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetConditionNode() {
  this.addOutput('Condition', 'boolean')
  this.addInput('Name', 'string')

  this.serialize_widgets = true
}

GetConditionNode.title = 'Get condition'

LiteGraph.registerNodeType('tools/get_condition', GetConditionNode)

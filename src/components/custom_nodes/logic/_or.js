// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function OrNode() {
  this.addInput('Condition', 'boolean')
  this.addInput('Condition', 'boolean')

  this.addOutput('Condition', 'boolean')

  this.serialize_widgets = true
}

OrNode.title = 'OR'

LiteGraph.registerNodeType('logic/or', OrNode)

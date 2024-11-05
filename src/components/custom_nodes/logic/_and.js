// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function AndNode() {
  this.addInput('Condition', 'boolean')
  this.addInput('Condition', 'boolean')

  this.addOutput('True', 'boolean')
  this.addOutput('False', 'boolean')

  this.serialize_widgets = true
}

AndNode.title = 'AND'

LiteGraph.registerNodeType('logic/and', AndNode)

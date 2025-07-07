// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function SmallerNode() {
  this.addInput('Float', 'float')
  this.addInput('Float', 'float')

  this.addOutput('Bool', 'bool')

  this.serialize_widgets = true
}

SmallerNode.title = 'Smaller'

LiteGraph.registerNodeType('compare/smaller', SmallerNode)

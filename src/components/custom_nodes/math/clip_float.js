// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function ClipFloatNode() {
  this.addInput('Min', 'float')
  this.addInput('Max', 'float')
  this.addInput('Value', 'float')

  this.addOutput('Float', 'float')

  this.serialize_widgets = true
}

ClipFloatNode.title = 'Clip Float'

LiteGraph.registerNodeType('math/clip_float', ClipFloatNode) 
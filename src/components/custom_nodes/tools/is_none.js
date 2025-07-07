// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function IsNone() {
  this.addInput('Value', '')
  this.addOutput('None?', 'bool')
  this.serialize_widgets = true
}

IsNone.title = 'Is None'

LiteGraph.registerNodeType('trade/is_none', IsNone)

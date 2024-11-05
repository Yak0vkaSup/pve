// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function SetStringNode() {
  this.addOutput('String', 'string')
  this.properties = {
    value: 'String' // You can set this to an empty string or any default
  }
  this.addWidget(
    'text',
    'Value',
    this.properties.value,
    (value) => {
      this.properties.value = value
    }
  )
  this.serialize_widgets = true
}

SetStringNode.title = 'Set string'

LiteGraph.registerNodeType('set/string', SetStringNode)

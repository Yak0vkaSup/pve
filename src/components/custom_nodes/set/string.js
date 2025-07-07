// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function SetStringNode() {
  this.addOutput('String', 'string')
  this.properties = {
    value: 'Hello!' // You can set this to an empty string or any default
  }
  this.addWidget(
    'text',
    '',
    this.properties.value,
    (value) => {
      this.properties.value = value
    }
  )
  this.widgets_up = true;
  this.size = [100,30]
  this.serialize_widgets = true
}

SetStringNode.title = 'Set string'

LiteGraph.registerNodeType('set/string', SetStringNode)

// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function SetIntegerNode() {
  this.addOutput('Integer', 'integer')
  this.properties = {
    value: 3
  }
  this.addWidget("number", "Value", this.properties.value, (value) => {
    const intValue = parseInt(value, 10);
    if (!isNaN(intValue)) {
      this.properties.value = intValue;
    }
  }, {
    property: "value",
    step: 10,
    min: Number.MIN_SAFE_INTEGER,
    max: Number.MAX_SAFE_INTEGER,
    precision: 0
  });

  this.serialize_widgets = true
}

SetIntegerNode.title = 'Set integer'
SetIntegerNode.description = 'Set integer'

LiteGraph.registerNodeType('set/integer', SetIntegerNode)

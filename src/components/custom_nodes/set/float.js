// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function SetFloatNode() {
  this.addOutput('Float', 'float')
  this.properties = {
    value: 1.0
  }

  this.addWidget("number", "", this.properties.value, (value) => {
    const floatValue = parseFloat(value);
    if (!isNaN(floatValue)) {
      this.properties.value = floatValue;
    }
  }, {
    property: "value",
    step: 0.01,
    min: -Infinity,
    max: Infinity,
    precision: 3
  });
  this.widgets_up = true;
  this.size = [125,30]
  this.title_color = "#87CEFA";

  this.serialize_widgets = true;
}

SetFloatNode.title = 'Set float'

LiteGraph.registerNodeType('set/float', SetFloatNode)

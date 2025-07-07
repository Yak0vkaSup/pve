import { LiteGraph } from 'litegraph.js'

export function SetBoolNode() {
  // Define one boolean output
  this.addOutput('Bool', 'bool')
  // Default property is false
  this.properties = {
    value: true
  }

  // Add a toggle widget to let the user switch the boolean value.
  // If your LiteGraph version doesn’t support "toggle", consider using a "combo" widget.
  this.addWidget("toggle", "", this.properties.value, (value) => {
    // Ensure the value is interpreted as a boolean.
    this.properties.value = Boolean(value);
  }, {
    property: "value"
  });

  // Set the node dimensions and styling.
  this.widgets_up = true;
  this.size = [100, 30]
  this.title_color = "#87CEFA";
  this.serialize_widgets = true;
}

SetBoolNode.title = 'Set bool';

// Register the node under a unique type.
LiteGraph.registerNodeType('set/bool', SetBoolNode);

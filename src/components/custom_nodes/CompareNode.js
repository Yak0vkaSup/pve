import { LiteGraph } from 'litegraph.js';

export function ComparaisonNode() {
  // Add two inputs for comparison, specifying the slot colors
  this.addInput('First Input', 'column', {
  });

  this.addInput('Second Input', 'column', {
  });

  // Add an output for the boolean result, specifying the slot colors
  this.addOutput('Bool Output', 'bool_column', {
  });

  // Define properties (the comparison operator)
  this.properties = {
    operator: '==' // Default comparison operator
  };

  // Add a dropdown widget to choose the comparison operator
  this.addWidget(
    'combo',
    'operator',
    this.properties.operator,
    (value) => {
      this.properties.operator = value;
    },
    {
      values: ['>', '>=', '<', '<=', '==', 'crossed up', 'crossed down'] // Supported operators
    }
  );

  // Ensure the widgets are serialized with the node
  this.serialize_widgets = true;
}

// Set the title for the node
ComparaisonNode.title = 'Comparaison';

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/data/comparaison', ComparaisonNode);

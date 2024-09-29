// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetAllIndicatorsNode() {
    // Initialize node with a single input and output
    this.addInput("Indicator", "dataframe");
    this.addOutput("List of indicators", "list");

    // Initial properties
    this.properties = {
        factor: 1,
        numInputs: 1 // Track the number of inputs
    };

    // Add the "Add Input" button using addWidget
    this.addWidget("button", "Add Input", null, () => {
        // Increment numInputs and update inputs when button is pressed
        this.properties.numInputs += 1;
        this.updateInputs();
    });
    this.addWidget("button", "Delete Input", null, () => {
      // Increment numInputs and update inputs when button is pressed
      this.properties.numInputs += -1;
      this.updateInputs();
  });

    // Method to dynamically add inputs based on numInputs property
    this.updateInputs = function() {
        const currentInputs = this.inputs.length;
        const desiredInputs = this.properties.numInputs;

        // Add inputs if numInputs is increased
        for (let i = currentInputs; i < desiredInputs; i++) {
            this.addInput(`Indicator ${i + 1}`, "dataframe");
        }

        // Remove inputs if numInputs is decreased
        for (let i = currentInputs; i > desiredInputs; i--) {
            this.removeInput(i - 1); // Remove input at the end
        }

        // Adjust the size based on the number of inputs
        this.setSize(this.computeSize());
    };

    // Triggered when a property changes
    this.onPropertyChanged = function(name, value) {
        if (name === 'numInputs') {
            this.updateInputs();  // Update inputs when numInputs property is changed
        }
    };
}

// Set the title for the node
GetAllIndicatorsNode.title = "Assemble indicators";

// Register the node with LiteGraph
LiteGraph.registerNodeType("custom/data/getallindicatorsnode", GetAllIndicatorsNode);

// Import LiteGraph
import { LiteGraph } from 'litegraph.js';

export function VizualizeData() {
  // Initialize the base node with four fixed inputs
  this.addInput('Open', 'column');
  this.addInput('High', 'column');
  this.addInput('Low', 'column');
  this.addInput('Close', 'column');

  // Initialize properties
  this.properties = {
    indicators: [], // List to hold indicator names
  };

  // Add "Add Indicator" button and keep a reference
  this.addIndicatorButton = this.addWidget(
    "button",
    "Add Indicator",
    null,
    () => {
      this.addIndicator();
    }
  );

  // Add "Remove Indicator" button and keep a reference
  this.removeIndicatorButton = this.addWidget(
    "button",
    "Remove Indicator",
    null,
    () => {
      this.removeIndicator();
    }
  );

  // Initially disable the "Remove Indicator" button since there are no indicators
  this.removeIndicatorButton.disabled = true;

  // Render the node with initial size
  this.size = [200, 150];

  // Ensure widgets are serialized with the node
  this.serialize_widgets = true;
}

// Set the title for the node
VizualizeData.title = 'Vizualize';

// Method to add a new Indicator input
VizualizeData.prototype.addIndicator = function() {
  const newIndicatorName = `Indicator ${this.properties.indicators.length + 1}`;

  // Add to properties
  this.properties.indicators.push(newIndicatorName);

  // Add a new input for the indicator
  this.addInput(newIndicatorName, 'column');

  // Optionally, update node size or appearance
  this.size[1] += 0; // Increase height to accommodate new input

  // Enable the "Remove Indicator" button since there is at least one indicator now
  if (this.properties.indicators.length > 0) {
    this.removeIndicatorButton.disabled = false;
  }

  // Trigger UI update
  this.setDirtyCanvas(true);
};

// Method to remove the last Indicator input
VizualizeData.prototype.removeIndicator = function() {
  if (this.properties.indicators.length === 0) {
    console.warn("No indicators to remove.");
    return;
  }

  // Remove from properties
  this.properties.indicators.pop();

  // Calculate the input index to remove
  const inputIndex = 4 + this.properties.indicators.length; // Fixed inputs are first 4

  // Remove the corresponding input
  this.removeInput(inputIndex);

  // Optionally, update node size or appearance
  this.size[1] -= 0; // Decrease height as an input is removed

  // Disable the "Remove Indicator" button if no indicators remain
  if (this.properties.indicators.length === 0) {
    this.removeIndicatorButton.disabled = true;
  }

  // Trigger UI update
  this.setDirtyCanvas(true);
};

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/data/vizualize', VizualizeData);

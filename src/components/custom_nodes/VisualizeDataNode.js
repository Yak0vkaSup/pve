// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function VizualizeData() {
  this.addInput('Open', 'dataframe')
  this.addInput('High', 'dataframe')
  this.addInput('Low', 'dataframe')
  this.addInput('Close', 'dataframe')
  this.addInput('Indicators list', 'list')
}

// Set the title for the node
VizualizeData.title = 'Vizualize Data'

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/vizualize', VizualizeData)

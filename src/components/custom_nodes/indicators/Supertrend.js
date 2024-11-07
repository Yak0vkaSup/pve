// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function SuperTrendNode() {
  // this.addInput('Data', 'number')
  this.addInput('High', 'column')
  this.addInput('Low', 'column')
  this.addInput('Close', 'column')

  this.addInput('Window', 'integer')

  this.addOutput('SuperTrend', 'column')

  this.serialize_widgets = true
}

// Set the title for the node
SuperTrendNode.title = 'SuperTrend'

// Register the node with LiteGraph
LiteGraph.registerNodeType('indicators/super_trend', SuperTrendNode)

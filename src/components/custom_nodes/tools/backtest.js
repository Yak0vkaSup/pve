// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function BacktestNode() {
  this.addInput('Entry condition', 'column')
  this.addInput('Take Profit', 'float')
  this.addInput('Fee %', 'float')

  this.serialize_widgets = true
}

BacktestNode.title = 'Get column'

LiteGraph.registerNodeType('tools/backtest', BacktestNode)

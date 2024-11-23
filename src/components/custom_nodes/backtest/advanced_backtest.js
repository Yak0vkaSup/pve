// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function AdvancedBacktestNode() {
  this.addInput('Signals', 'boolean')
  this.addInput('Profit target', 'float')
  this.addInput('Number of orders', 'integer')
  this.addInput('Martingale', 'float')
  this.addInput('Candles to close', 'integer')
  this.addInput('Step %', 'float')
  this.addInput('First order size', 'integer')


  this.serialize_widgets = true
}

AdvancedBacktestNode.title = 'Advanced Backtest'

LiteGraph.registerNodeType('backtest/advanced_backtest', AdvancedBacktestNode)

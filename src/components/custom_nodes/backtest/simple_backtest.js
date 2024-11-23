// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function SimpleBacktestNode() {
  this.addInput('Signals', 'boolean')
  this.addInput('Profit target', 'float')
  // this.addInput('Number of orders', 'integer')
  // this.addInput('Martingale', 'float')
  // this.addInput('Step %', 'float')

  this.addInput('Candles to close', 'integer')
  this.addInput('First order size', 'integer')


  this.serialize_widgets = true
}

SimpleBacktestNode.title = 'Simple Backtest'

LiteGraph.registerNodeType('backtest/simple_backtest', SimpleBacktestNode)

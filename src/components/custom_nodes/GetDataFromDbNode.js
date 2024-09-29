// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetDataFromDbNode() {
  // this.addInput('Data', 'number')
  this.addOutput('Open', 'dataframe')
  this.addOutput('High', 'dataframe')
  this.addOutput('Low', 'dataframe')
  this.addOutput('Close', 'dataframe')
  this.addOutput('Volume', 'dataframe')

  // Helper function to format the date to YYYY/MM/DD
  const getFormattedDate = (offsetDays = 0) => {
    const date = new Date()
    date.setDate(date.getDate() + offsetDays) // Adjust the date by offsetDays
    return date.toISOString().split('T')[0].replace(/-/g, '/') // Convert to YYYY/MM/DD
  }

  this.properties = {
    precision: 1,
    symbol: 'TONUSDT',
    startDate: getFormattedDate(-3), // 3 days before the current date
    endDate: getFormattedDate()      // Current date
  }
}

// Set the title for the node
GetDataFromDbNode.title = 'Get data'

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/data/get', GetDataFromDbNode)

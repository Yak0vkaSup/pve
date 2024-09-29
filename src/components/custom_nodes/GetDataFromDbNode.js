// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetDataFromDbNode() {
  // this.addInput('Data', 'number')
  this.addOutput ("Open", "dataframe");
  this.addOutput ("High", "dataframe");
  this.addOutput ("Low", "dataframe");
  this.addOutput ("Close", "dataframe");
  this.addOutput ("Volume", "dataframe");

  const getFormattedDate = () => {
    const date = new Date();
    return date.toISOString().split('T')[0].replace(/-/g, '/'); // Convert to YYYY/MM/DD
  };

  this.properties = { 
    precision: 1,
    symbol: "TONUSDT",
    startDate: getFormattedDate(),
    endDate: getFormattedDate(),
   };
}

// Set the title for the node
GetDataFromDbNode.title = 'Get data From DB'

// Register the node with LiteGraph
LiteGraph.registerNodeType('custom/data/get', GetDataFromDbNode)

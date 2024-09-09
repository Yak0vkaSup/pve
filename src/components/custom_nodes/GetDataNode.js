import { LiteGraph } from 'litegraph.js';

export function FetchDataNode() {
    this.addInput("symbol", "string");
    this.addOutput("candle_data", "object");
    this.properties = { symbol: "DOGSUSDT" }; // Default symbol
}

FetchDataNode.title = "Fetch Data Node";
FetchDataNode.desc = "Fetch data from the backend";

// Function to fetch data from the backend API
async function fetchData(symbol) {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/fetch-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                symbol: symbol,
                start_date: '2024-07-29 00:51:00+00',
            }),
        });

        if (!response.ok) {
            throw new Error(`Error: ${response.status}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

FetchDataNode.prototype.onExecute = async function() {
    const symbol = this.getInputData(0) || this.properties.symbol; // Get the symbol from input or use default

    // Fetch data only if the symbol exists
    if (symbol) {
        const data = await fetchData(symbol);
        if (data) {
            this.setOutputData(0, data);  // Set the fetched data as the output
        }
    }
};

LiteGraph.registerNodeType("data/fetch_data", FetchDataNode);

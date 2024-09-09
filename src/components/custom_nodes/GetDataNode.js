import { LiteGraph } from 'litegraph.js';

function FetchDataNode() {
    this.addInput("symbol", "string");
    this.addInput("start_date", "string");
    this.addInput("end_date", "string");
    this.addOutput("candle_data", "object");
    this.properties = { symbol: "", start_date: "", end_date: "" };
}

FetchDataNode.title = "Fetch Data Node";
FetchDataNode.desc = "Fetch data from the backend";

FetchDataNode.prototype.onExecute = async function() {
    const symbol = this.getInputData(0) || this.properties.symbol;
    const start_date = this.getInputData(1) || this.properties.start_date;
    const end_date = this.getInputData(2) || this.properties.end_date;

    if (symbol && start_date && end_date) {
        // Call the backend API to fetch data
        const response = await fetch("/api/fetch-data", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                symbol: symbol,
                start_date: start_date,
                end_date: end_date,
            }),
        });
        const data = await response.json();
        this.setOutputData(0, data);
    }
};

LiteGraph.registerNodeType("data/fetch_data", FetchDataNode);

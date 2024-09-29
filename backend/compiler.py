import pandas as pd
import json

class Node:
    def __init__(self, node_data):
        self.id = node_data['id']
        self.type = node_data['type']
        self.properties = node_data['properties']
        self.inputs = node_data.get('inputs', [])
        self.outputs = node_data.get('outputs', [])
    
    def __repr__(self):
        return f"Node(id={self.id}, type={self.type}, properties={self.properties})"

def compile(graph_data):
    connected_nodes = []
    for node in graph_data['nodes']:
        is_connected = False

        # Check if any outputs are linked
        for output in node.get('outputs', []):
            if output.get('links') is not None and len(output.get('links', [])) > 0:
                is_connected = True
                break

        # Check if any inputs are linked
        for input_ in node.get('inputs', []):
            if input_.get('link') is not None:
                is_connected = True
                break

        if is_connected:
            connected_nodes.append(node)

    nodes_objects = [Node(node) for node in connected_nodes]

    # Print out the nodes to verify
    for node in nodes_objects:
        print(node.outputs)
    

if __name__ == "__main__":
    jsonpve = """
    {
    "extra": {},
    "links": [
        [
        4,
        2,
        0,
        1,
        0,
        "dataframe"
        ],
        [
        5,
        2,
        1,
        1,
        1,
        "dataframe"
        ],
        [
        6,
        2,
        2,
        1,
        2,
        "dataframe"
        ],
        [
        7,
        2,
        3,
        1,
        3,
        "dataframe"
        ],
        [
        8,
        2,
        4,
        6,
        0,
        "dataframe"
        ]
    ],
    "nodes": [
        {
        "id": 1,
        "pos": [
            804,
            142
        ],
        "mode": 0,
        "size": {
            "0": 140,
            "1": 86
        },
        "type": "custom/vizualize",
        "flags": {
            "collapsed": false
        },
        "order": 3,
        "inputs": [
            {
            "link": 4,
            "name": "Open",
            "type": "dataframe"
            },
            {
            "link": 5,
            "name": "High",
            "type": "dataframe"
            },
            {
            "link": 6,
            "name": "Low",
            "type": "dataframe"
            },
            {
            "link": 7,
            "name": "Close",
            "type": "dataframe"
            }
        ],
        "properties": {}
        },
        {
        "id": 6,
        "pos": [
            493,
            388
        ],
        "mode": 0,
        "size": {
            "0": 210,
            "1": 58
        },
        "type": "custom/indicators/ma",
        "flags": {},
        "order": 4,
        "inputs": [
            {
            "link": 8,
            "name": "Close",
            "type": "dataframe"
            }
        ],
        "outputs": [
            {
            "name": "ma",
            "type": "dataframe",
            "links": null
            }
        ],
        "properties": {
            "windows": 7,
            "precision": "trima"
        }
        },
        {
        "id": 5,
        "pos": [
            520,
            309
        ],
        "mode": 0,
        "size": {
            "0": 140,
            "1": 26
        },
        "type": "custom/indicators/rsi",
        "flags": {},
        "order": 0,
        "inputs": [
            {
            "link": null,
            "name": "Close",
            "type": "dataframe"
            }
        ],
        "outputs": [
            {
            "name": "rsi",
            "type": "dataframe",
            "links": null,
            "slot_index": 0
            }
        ],
        "properties": {
            "windows": 14000
        }
        },
        {
        "id": 4,
        "pos": [
            749,
            317
        ],
        "mode": 0,
        "size": {
            "0": 140,
            "1": 66
        },
        "type": "custom/indicators/bollinger",
        "flags": {},
        "order": 1,
        "inputs": [
            {
            "link": null,
            "name": "Close",
            "type": "dataframe"
            }
        ],
        "outputs": [
            {
            "name": "Lower",
            "type": "dataframe",
            "links": null,
            "slot_index": 0
            },
            {
            "name": "Mid",
            "type": "dataframe",
            "links": null,
            "slot_index": 1
            },
            {
            "name": "Upper",
            "type": "dataframe",
            "links": null,
            "slot_index": 2
            }
        ],
        "properties": {
            "windows": 7
        }
        },
        {
        "id": 2,
        "pos": [
            289,
            197
        ],
        "mode": 0,
        "size": {
            "0": 140,
            "1": 106
        },
        "type": "custom/data/get",
        "flags": {},
        "order": 2,
        "outputs": [
            {
            "name": "Open",
            "type": "dataframe",
            "links": [
                4
            ],
            "slot_index": 0
            },
            {
            "name": "High",
            "type": "dataframe",
            "links": [
                5
            ],
            "slot_index": 1
            },
            {
            "name": "Low",
            "type": "dataframe",
            "links": [
                6
            ],
            "slot_index": 2
            },
            {
            "name": "Close",
            "type": "dataframe",
            "links": [
                7
            ],
            "slot_index": 3
            },
            {
            "name": "Volume",
            "type": "dataframe",
            "links": [
                8
            ],
            "slot_index": 4
            }
        ],
        "properties": {
            "symbol": "TONUSDT",
            "endDate": "2024/09/29",
            "precision": 1,
            "startDate": "2024/09/29"
        }
        }
    ],
    "config": {},
    "groups": [],
    "version": 0.4,
    "last_link_id": 8,
    "last_node_id": 6
    }
    """
    graph_data=json.loads(jsonpve)
    compile(graph_data)
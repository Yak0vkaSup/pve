# app/nodes/nodes.py
import logging
import pandas as pd
import pandas_ta as ta
import json
from flask import current_app
from ..socketio_setup import socketio

from .utils import (
    fetch_data,
    get_open,
    get_close,
    get_high,
    get_low,
    get_volume,
    add_column,
    delete_column,
    multiply_column
)

# Configure logging for this module
logger = logging.getLogger(__name__)

class Node:
    df = None
    def __init__(self, node_id, node_type, properties, inputs, outputs):
        self.id = node_id
        self.type = node_type
        self.properties = properties
        self.inputs = inputs  # List of input definitions
        self.outputs = outputs  # List of output definitions
        self.input_values = {}  # Actual input data
        self.output_values = {}  # Actual output data
        self.input_connections = {}  # Mapping from input slots to (origin_node, origin_slot)
        self.output_connections = {}  # Mapping from output slots to list of (target_node, target_slot)

    @classmethod
    def set_df(cls, df):
        cls.df = df

    @classmethod
    def get_df(cls):
        return cls.df


class GetOpenNode(Node):
    def execute(self):
        df = Node.get_df()
        if df is not None:
            open_series = get_open(df)
            self.output_values['open'] = open_series
            logger.info(f"GetOpenNode {self.id}: Output 'column' set.")
        else:
            logger.error(f"GetOpenNode {self.id}: DataFrame is None.")
            self.output_values['open'] = None

class SetFloatNode(Node):
    def execute(self):
        float_value = self.properties.get('value', 1.0)
        logger.info(f"SetFloatNode {self.id}: Set float value to {float_value}.")
        self.output_values['Float'] = float_value

class SetStringNode(Node):
    def execute(self):
        string_value = self.properties.get('value', '')
        logger.info(f"SetStringNode {self.id}: Set string value to '{string_value}'.")
        self.output_values['String'] = string_value

class MultiplyColumnNode(Node):
    def execute(self):
        print(self.input_values)
        source_column = self.input_values.get(0)  # Assuming input slot 0 is the source Series
        factor = self.input_values.get(1)  # Assuming input slot 1 is the coefficient (float)

        if source_column is None:
            logger.error(f"MultiplyColumnNode {self.id}: Source column is None.")
            self.output_values['Result'] = None
            return

        if factor is None:
            logger.error(f"MultiplyColumnNode {self.id}: Factor is None.")
            self.output_values['Result'] = None
            return

        try:
            multiplied_series = multiply_column(source_column, factor)
            self.output_values['Result'] = multiplied_series
            logger.info(f"MultiplyColumnNode {self.id}: Multiplied column '{source_column.name}' by {factor}.")
        except Exception as e:
            logger.error(f"MultiplyColumnNode {self.id}: {e}")
            self.output_values['Result'] = None



class AddColumnNode(Node):
    def execute(self):
        df = Node.get_df()
        if df is not None:
            source_series = self.input_values.get(0)  # Input slot 0: Column (pd.Series)
            column_name = self.input_values.get(1)     # Input slot 1: Name (str)

            if source_series is None:
                logger.error(f"AddColumnNode {self.id}: Source column is None.")
                return

            if column_name is None:
                logger.error(f"AddColumnNode {self.id}: Column name is None.")
                return

            try:
                updated_df = df.copy()
                updated_df = add_column(updated_df, column_name, source_series)
                Node.set_df(updated_df)
                logger.info(f"AddColumnNode {self.id}: Added column '{column_name}'.")
            except Exception as e:
                logger.error(f"AddColumnNode {self.id}: {e}")

        else:
            logger.error(f"AddColumnNode {self.id}: DataFrame is None.")

# Graph Processing Functions
def build_nodes(nodes_data):
    nodes = {}
    for node_data in nodes_data:
        node_id = node_data['id']
        node_type = node_data['type']
        properties = node_data.get('properties', {})
        inputs = node_data.get('inputs', [])
        outputs = node_data.get('outputs', [])

        if node_type == 'get/open':
            node = GetOpenNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'tools/add_column':
            node = AddColumnNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'math/multiply_column':
            node = MultiplyColumnNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'set/float':
            node = SetFloatNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'set/string':
            node = SetStringNode(node_id, node_type, properties, inputs, outputs)
        else:
            logger.warning(f"Unknown node type: {node_type}")
            node = Node(node_id, node_type, properties, inputs, outputs)

        nodes[node_id] = node
    return nodes

def build_connections(links_data, nodes):
    for link in links_data:
        link_id, origin_id, origin_slot, target_id, target_slot, link_type = link
        origin_node = nodes[origin_id]
        target_node = nodes[target_id]

        # Map the connection
        target_node.input_connections[target_slot] = (origin_node, origin_slot)

        # Log the connection
        logger.debug(f"Connecting Node {origin_id} Output Slot {origin_slot} ('{origin_node.outputs[origin_slot]['name']}') "
                     f"to Node {target_id} Input Slot {target_slot}")

        # Map the output links as well
        if origin_slot not in origin_node.output_connections:
            origin_node.output_connections[origin_slot] = []
        origin_node.output_connections[origin_slot].append((target_node, target_slot))

def build_graph(nodes):
    graph = {}
    in_degree = {}
    for node_id in nodes:
        graph[node_id] = []
        in_degree[node_id] = 0

    for node in nodes.values():
        for targets in node.output_connections.values():
            for target_node, _ in targets:
                graph[node.id].append(target_node.id)
                in_degree[target_node.id] += 1
    return graph, in_degree

def topological_sort(nodes, graph, in_degree):
    sorted_nodes = []
    queue = [node_id for node_id in nodes if in_degree[node_id] == 0]

    while queue:
        node_id = queue.pop(0)
        sorted_nodes.append(node_id)

        for neighbor in graph[node_id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_nodes) != len(nodes):
        raise Exception("Graph has a cycle!")
    return sorted_nodes

def execute_graph(sorted_node_ids, nodes):
    for node_id in sorted_node_ids:
        node = nodes[node_id]
        # Prepare input values
        for input_slot_index, (origin_node, origin_slot_index) in node.input_connections.items():
            output_name = origin_node.outputs[origin_slot_index]['name']
            node.input_values[input_slot_index] = origin_node.output_values.get(output_name)
        logger.info(f"Executing Node {node_id} of type {node.type}")
        node.execute()


def process_graph(graph_json, start_date, end_date, symbol):
    logger.info("Starting graph processing")

    # Check if graph_data is a string (JSON), and load it if necessary
    if isinstance(graph_json, str):
        data = json.loads(graph_json)
        logger.debug("Loaded graph data from JSON string.")
    elif isinstance(graph_json, dict):
        data = graph_json
        logger.debug("Graph data is already a dictionary.")
    else:
        logger.error(f"Invalid type for graph_json: {type(graph_json)}")
        raise ValueError("graph_json must be a JSON string or a dictionary.")

    df = fetch_data(symbol, start_date, end_date)

    Node.set_df(df)

    nodes = build_nodes(data['nodes'])
    build_connections(data['links'], nodes)

    graph, in_degree = build_graph(nodes)
    sorted_node_ids = topological_sort(nodes, graph, in_degree)
    logger.info(f"Execution order: {sorted_node_ids}")

    execute_graph(sorted_node_ids, nodes)

    final_df = Node.get_df()

    if final_df is not None:
        logger.info("Processing complete. Retrieved final DataFrame from shared Node.df.")
    else:
        logger.error("No valid output DataFrame found after processing")

    return final_df
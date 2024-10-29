# app/nodes/nodes.py
import logging
import pandas as pd
import pandas_ta as ta
import json

from flask import current_app

from .utils import fetch_data, calculate_ma

# Configure logging for this module
logger = logging.getLogger(__name__)

class Node:
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

    def execute(self):
        raise NotImplementedError("Execute method not implemented for base Node class.")

# Specific Node Implementations

class GetDataNode(Node):
    def execute(self):
        logger.info(f"Executing GetDataNode {self.id}")
        symbol = self.properties.get('symbol', 'BTCUSDT')
        start_date = self.properties.get('startDate')
        end_date = self.properties.get('endDate')

        # Fetch data using fetch_data function
        df = fetch_data(symbol, start_date, end_date)
        if df is not None:
            self.output_values['DataFrame'] = df
            # Set outputs for each column
            for output in self.outputs:
                output_name = output['name']
                if output_name in df.columns:
                    # Pass the DataFrame and the column name
                    self.output_values[output_name] = (df, output_name)
                else:
                    logger.warning(f"GetDataNode {self.id}: Column '{output_name}' not found in data.")
                    self.output_values[output_name] = (df, None)
        else:
            logger.error(f"GetDataNode {self.id}: Failed to fetch data for symbol {symbol}")
            # Set outputs to (None, None)
            for output in self.outputs:
                output_name = output['name']
                self.output_values[output_name] = (None, None)

class MaNode(Node):
    def execute(self):
        logger.info(f"Executing MaNode {self.id}")
        input_slot = 0  # Assuming the input is always at slot 0
        if input_slot in self.input_connections:
            origin_node, origin_slot = self.input_connections[input_slot]
            output_name = origin_node.outputs[origin_slot]['name']
            input_data = origin_node.output_values.get(output_name)
        else:
            logger.warning(f"MaNode {self.id}: No input data.")
            return

        if input_data is None or input_data[0] is None:
            logger.warning(f"MaNode {self.id}: Input data is None.")
            return

        df, column_name = input_data
        if df is None or column_name is None:
            logger.warning(f"MaNode {self.id}: DataFrame or column name is None.")
            return

        # Extract properties for MA calculation
        mode = self.properties.get('mode', 'ema')
        window = int(self.properties.get('windows', 7))
        ma_multiplier = float(self.properties.get('ma_multiplier', 1.0))
        calculate_on = column_name

        # Calculate MA
        try:
            ma_values = calculate_ma(df, window, mode, calculate_on, ma_multiplier)
            ma_column_name = f"{mode.upper()}_{window}"
            df[ma_column_name] = ma_values
            self.output_values['MA'] = (df, ma_column_name)
            logger.info(f"MaNode {self.id}: MA column '{ma_column_name}' calculated successfully.")
        except Exception as e:
            logger.error(f"MaNode {self.id}: Error during MA calculation: {e}")
            self.output_values['MA'] = (None, None)


class MultiplyColumnNode(Node):
    def execute(self):
        logger.info(f"Executing MultiplyColumnNode {self.id}")
        # Retrieve input data
        input_slot = 0
        if input_slot in self.input_connections:
            origin_node, origin_slot = self.input_connections[input_slot]
            output_name = origin_node.outputs[origin_slot]['name']
            input_data = origin_node.output_values.get(output_name)
        else:
            logger.warning(f"MultiplyColumnNode {self.id}: No input data.")
            self.output_values['Result'] = (None, None)
            return

        if not input_data or not input_data[0]:
            logger.warning(f"MultiplyColumnNode {self.id}: Input data is None.")
            self.output_values['Result'] = (None, None)
            return

        df, column_name = input_data
        if not df or not column_name:
            logger.warning(f"MultiplyColumnNode {self.id}: DataFrame or column name is None.")
            self.output_values['Result'] = (None, None)
            return

        # Validate 'factor'
        try:
            factor = float(self.properties.get('factor', 1.0))
            if not (0.000 <= factor <= 100.0):
                raise ValueError(f"'factor' {factor} is out of bounds [0.000, 100.000].")
        except (ValueError, TypeError) as e:
            logger.error(f"MultiplyColumnNode {self.id}: Invalid 'factor' value: {e}")
            self.output_values['Result'] = (df, None)
            return

        # Perform multiplication
        try:
            new_column_name = f"{column_name}_x_{factor}"
            df[new_column_name] = df[column_name] * factor
            logger.info(f"MultiplyColumnNode {self.id}: Created new column '{new_column_name}'.")
            self.output_values['Result'] = (df, new_column_name)
        except Exception as e:
            logger.error(f"MultiplyColumnNode {self.id}: Error during multiplication: {e}")
            self.output_values['Result'] = (None, None)

class VizualizeDataNode(Node):
    def execute(self):
        logger.info(f"Executing VizualizeDataNode {self.id}")
        columns_to_keep = ['date', 'open', 'high', 'low', 'close']
        base_df = None

        # Process all inputs
        for input_slot, (origin_node, origin_slot) in self.input_connections.items():
            output_name = origin_node.outputs[origin_slot]['name']
            input_data = origin_node.output_values.get(output_name)
            logger.debug(f"Input data for slot {input_slot}: {input_data}")

            if input_data is None or input_data[0] is None:
                logger.warning(f"VizualizeDataNode {self.id}: Input data is None for slot {input_slot}")
                continue

            df, column_name = input_data
            if df is None or column_name is None:
                logger.warning(f"VizualizeDataNode {self.id}: DataFrame or column name is None for slot {input_slot}")
                continue

            columns_to_keep.append(column_name)

            if base_df is None:
                base_df = df.copy()
                logger.debug(f"VizualizeDataNode {self.id}: Base DataFrame set with columns {base_df.columns.tolist()}")
            else:
                try:
                    base_df = base_df.merge(df[['date', column_name]], on='date', how='left')
                    logger.debug(f"VizualizeDataNode {self.id}: Merged column '{column_name}' into base DataFrame.")
                except KeyError as e:
                    logger.error(f"VizualizeDataNode {self.id}: Error merging DataFrame on 'date': {e}")
                    continue

        if base_df is None:
            logger.error(f"VizualizeDataNode {self.id}: No valid input DataFrame found.")
            self.output_values['Filtered DataFrame'] = None
            return

        # Ensure all required columns are present
        missing_columns = [col for col in columns_to_keep if col not in base_df.columns]
        if missing_columns:
            logger.warning(f"VizualizeDataNode {self.id}: Missing columns after merge: {missing_columns}")
            for col in missing_columns:
                base_df[col] = None
            logger.debug(f"VizualizeDataNode {self.id}: Added missing columns with default values.")

        try:
            df_filtered = base_df[columns_to_keep]
            logger.info(f"VizualizeDataNode {self.id}: Filtered DataFrame created with columns {df_filtered.columns.tolist()}")
            self.output_values['Filtered DataFrame'] = df_filtered
        except KeyError as e:
            logger.error(f"VizualizeDataNode {self.id}: Error filtering DataFrame columns: {e}")
            self.output_values['Filtered DataFrame'] = None


class HeikinAshiNode(Node):
    def execute(self):
        logger.info(f"Executing HeikinAshiNode {self.id}")
        inputs = {}
        input_names = ['Open', 'High', 'Low', 'Close']
        input_slots = [0, 1, 2, 3]

        for slot, name in zip(input_slots, input_names):
            if slot in self.input_connections:
                origin_node, origin_slot = self.input_connections[slot]
                output_name = origin_node.outputs[origin_slot]['name']
                input_data = origin_node.output_values.get(output_name)
                if input_data and input_data[0] is not None:
                    df, column_name = input_data
                    if column_name in df.columns:
                        inputs[name] = df[column_name]
                    else:
                        logger.warning(f"HeikinAshiNode {self.id}: Column '{column_name}' not found in data.")
                        inputs[name] = None
                else:
                    logger.warning(f"HeikinAshiNode {self.id}: Input '{name}' data is None.")
                    inputs[name] = None
            else:
                logger.warning(f"HeikinAshiNode {self.id}: Input '{name}' not connected.")
                inputs[name] = None

        # Check that all inputs are present
        if any(value is None for value in inputs.values()):
            logger.error(f"HeikinAshiNode {self.id}: Missing input data.")
            self.output_values['HA_Open'] = (None, None)
            self.output_values['HA_High'] = (None, None)
            self.output_values['HA_Low'] = (None, None)
            self.output_values['HA_Close'] = (None, None)
            return

        # Assuming all inputs come from the same DataFrame
        origin_node, origin_slot = self.input_connections[0]
        base_df, _ = origin_node.output_values.get(origin_node.outputs[origin_slot]['name'])

        if base_df is None:
            logger.error(f"HeikinAshiNode {self.id}: Base DataFrame is None.")
            self.output_values['HA_Open'] = (None, None)
            self.output_values['HA_High'] = (None, None)
            self.output_values['HA_Low'] = (None, None)
            self.output_values['HA_Close'] = (None, None)
            return

        # Calculate Heikin Ashi
        try:
            df_ha = ta.ha(inputs['Open'], inputs['High'], inputs['Low'], inputs['Close'])
            base_df['HA_Open'] = df_ha['HA_open']
            base_df['HA_High'] = df_ha['HA_high']
            base_df['HA_Low'] = df_ha['HA_low']
            base_df['HA_Close'] = df_ha['HA_close']

            self.output_values['HA_Open'] = (base_df, 'HA_Open')
            self.output_values['HA_High'] = (base_df, 'HA_High')
            self.output_values['HA_Low'] = (base_df, 'HA_Low')
            self.output_values['HA_Close'] = (base_df, 'HA_Close')

            logger.info(f"HeikinAshiNode {self.id}: Successfully calculated Heikin Ashi columns.")
        except Exception as e:
            logger.error(f"HeikinAshiNode {self.id}: Error during Heikin Ashi calculation: {e}")
            self.output_values['HA_Open'] = (None, None)
            self.output_values['HA_High'] = (None, None)
            self.output_values['HA_Low'] = (None, None)
            self.output_values['HA_Close'] = (None, None)


class ComparisonNode(Node):
    def execute(self):
        logger.info(f"Executing ComparisonNode {self.id}")
        inputs = {}
        input_slots = [0, 1]
        input_names = ['First Input', 'Second Input']

        for slot, name in zip(input_slots, input_names):
            if slot in self.input_connections:
                origin_node, origin_slot = self.input_connections[slot]
                output_name = origin_node.outputs[origin_slot]['name']
                input_data = origin_node.output_values.get(output_name)

                # Explicitly check for None
                if input_data is not None and input_data[0] is not None:
                    df, column_name = input_data
                    if column_name in df.columns:
                        inputs[name] = df[column_name]
                    else:
                        logger.warning(f"ComparisonNode {self.id}: Column '{column_name}' not found in data.")
                        inputs[name] = None
                else:
                    logger.warning(f"ComparisonNode {self.id}: Input '{name}' data is None.")
                    inputs[name] = None
            else:
                logger.warning(f"ComparisonNode {self.id}: Input '{name}' not connected.")
                inputs[name] = None

        if inputs['First Input'] is None or inputs['Second Input'] is None:
            logger.error(f"ComparisonNode {self.id}: Missing input data.")
            self.output_values['bool_column'] = (None, None)
            return

        comparison_operator = self.properties.get('operator', '==')

        try:
            if comparison_operator == '>':
                comparison_result = inputs['First Input'] > inputs['Second Input']
            elif comparison_operator == '>=':
                comparison_result = inputs['First Input'] >= inputs['Second Input']
            elif comparison_operator == '<':
                comparison_result = inputs['First Input'] < inputs['Second Input']
            elif comparison_operator == '<=':
                comparison_result = inputs['First Input'] <= inputs['Second Input']
            elif comparison_operator == '==':
                comparison_result = inputs['First Input'] == inputs['Second Input']
            elif comparison_operator == 'crossed up':
                comparison_result = (inputs['First Input'] > inputs['Second Input']) & \
                                    (inputs['First Input'].shift(1) <= inputs['Second Input'].shift(1))
            elif comparison_operator == 'crossed down':
                comparison_result = (inputs['First Input'] < inputs['Second Input']) & \
                                    (inputs['First Input'].shift(1) >= inputs['Second Input'].shift(1))
            else:
                logger.error(f"ComparisonNode {self.id}: Unsupported operator '{comparison_operator}'.")
                self.output_values['bool_column'] = (None, None)
                return
        except Exception as e:
            logger.exception(f"ComparisonNode {self.id}: Error during comparison")
            self.output_values['bool_column'] = (None, None)
            return

        # Create new DataFrame to avoid modifying original
        origin_node, origin_slot = self.input_connections[0]
        base_df, _ = origin_node.output_values.get(origin_node.outputs[origin_slot]['name'])
        if base_df is None:
            logger.error(f"ComparisonNode {self.id}: Base DataFrame is None.")
            self.output_values['bool_column'] = (None, None)
            return

        new_df = base_df.copy()
        bool_column_name = f"bool_{comparison_operator.replace(' ', '_')}"
        new_df[bool_column_name] = comparison_result

        self.output_values['bool_column'] = (new_df, bool_column_name)
        logger.info(f"ComparisonNode {self.id}: Comparison column '{bool_column_name}' created.")


# Graph Processing Functions

def build_nodes(nodes_data):
    nodes = {}
    for node_data in nodes_data:
        node_id = node_data['id']
        node_type = node_data['type']
        properties = node_data.get('properties', {})
        inputs = node_data.get('inputs', [])
        outputs = node_data.get('outputs', [])

        if node_type == 'custom/data/getdata':
            node = GetDataNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'custom/indicators/ma':
            node = MaNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'custom/data/multiply':
            node = MultiplyColumnNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'custom/data/vizualize':
            node = VizualizeDataNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'custom/indicators/heikin_ashi':
            node = HeikinAshiNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'custom/data/comparaison':
            node = ComparisonNode(node_id, node_type, properties, inputs, outputs)
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


def process_graph(graph_json):
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

    nodes = build_nodes(data['nodes'])
    build_connections(data['links'], nodes)

    graph, in_degree = build_graph(nodes)
    sorted_node_ids = topological_sort(nodes, graph, in_degree)
    logger.info(f"Execution order: {sorted_node_ids}")

    execute_graph(sorted_node_ids, nodes)

    # Find the output DataFrame
    for node_id in reversed(sorted_node_ids):
        node = nodes[node_id]
        for output_value in node.output_values.values():
            if output_value is not None:
                if isinstance(output_value, tuple):
                    df, column_name = output_value
                    if df is not None:
                        logger.info(f"Processing complete. Output DataFrame from Node {node_id}.")
                        return df
                elif isinstance(output_value, pd.DataFrame):
                    df = output_value
                    logger.info(f"Processing complete. Output DataFrame from Node {node_id}.")
                    return df
                else:
                    logger.debug(f"process_graph: Unsupported output_value type {type(output_value)}")
    logger.error("No valid output DataFrame found after processing")
    return None

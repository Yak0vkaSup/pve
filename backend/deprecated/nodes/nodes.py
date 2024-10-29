import time
import pandas as pd
from pybit.unified_trading import HTTP
from pybit.unified_trading import WebSocket
import pandas_ta as ta
import psycopg2
import os
import logging
from datetime import datetime, timedelta
import json
from .utils import fetch_data, calculate_ma
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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
            node = ComparaisonNode(node_id, node_type, properties, inputs, outputs)
        else:
            node = Node(node_id, node_type, properties, inputs, outputs)

        nodes[node_id] = node
    return nodes

def build_connections(links_data, nodes):
    for link in links_data:
        link_id, origin_id, origin_slot, target_id, target_slot, link_type = link
        origin_node = nodes[origin_id]
        target_node = nodes[target_id]

        # Map the connection
        if not hasattr(target_node, 'input_connections'):
            target_node.input_connections = {}
        target_node.input_connections[target_slot] = (origin_node, origin_slot)

        # Log the connection
        logging.debug(f"Connecting Node {origin_id} Output Slot {origin_slot} ('{origin_node.outputs[origin_slot]['name']}') "
                      f"to Node {target_id} Input Slot {target_slot}")

        # Map the output links as well (optional)
        if not hasattr(origin_node, 'output_connections'):
            origin_node.output_connections = {}
        if origin_slot not in origin_node.output_connections:
            origin_node.output_connections[origin_slot] = []
        origin_node.output_connections[origin_slot].append((target_node, target_slot))


def execute_graph(sorted_node_ids, nodes):
    for node_id in sorted_node_ids:
        node = nodes[node_id]
        # Prepare input values
        for input_slot_index, (origin_node, origin_slot_index) in node.input_connections.items():
            output_name = origin_node.outputs[origin_slot_index]['name']
            node.input_values[input_slot_index] = origin_node.output_values.get(output_name)
        print(f"Executing Node {node_id} of type {node.type}")
        node.execute()

def build_graph(nodes):
    graph = {}
    in_degree = {}
    for node_id, node in nodes.items():
        graph[node_id] = []
        in_degree[node_id] = 0

    for node_id, node in nodes.items():
        for slot_index, targets in node.output_connections.items():
            for (target_node, target_slot) in targets:
                graph[node_id].append(target_node.id)
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


class GetDataNode(Node):
    def execute(self):
        symbol = self.properties.get('symbol', 'BTCUSDT')
        start_date = self.properties.get('startDate')
        end_date = self.properties.get('endDate')

        # Fetch data using fetch_data function
        df = fetch_data(symbol, start_date, end_date)
        if df is not None:
            self.output_values['DataFrame'] = df
            # Also, set outputs for each column
            for output in self.outputs:
                output_name = output['name']
                if output_name in df.columns:
                    # Pass the DataFrame and the column name
                    self.output_values[output_name] = (df, output_name)
                else:
                    print(f"GetDataNode {self.id}: Column {output_name} not found in data.")
                    self.output_values[output_name] = (df, None)
        else:
            print(f"GetDataNode {self.id}: Failed to fetch data for symbol {symbol}")
            # Set outputs to (None, None)
            for output in self.outputs:
                output_name = output['name']
                self.output_values[output_name] = (None, None)

class MaNode(Node):
    def execute(self):
        input_slot = 0  # Assuming the input is always at slot 0
        if input_slot in self.input_connections:
            origin_node, origin_slot = self.input_connections[input_slot]
            output_name = origin_node.outputs[origin_slot]['name']
            input_data = origin_node.output_values.get(output_name)
        else:
            print(f"Node {self.id}: No input data.")
            return

        if input_data is None or input_data[0] is None:
            print(f"Node {self.id}: Input data is None.")
            return

        df, column_name = input_data

        if df is None or column_name is None:
            print(f"Node {self.id}: DataFrame or column name is None.")
            return

        # Extract properties for MA calculation
        mode = self.properties.get('mode', 'ema')
        window = int(self.properties.get('windows', 7))
        ma_multiplier = self.properties.get('ma_multiplier', 1.0)
        # Use the column name from the input data
        calculate_on = column_name

        # Calculate MA
        try:
            ma_values = calculate_ma(df, window, mode, calculate_on, ma_multiplier)
            # Add the new MA column to the DataFrame
            ma_column_name = f"{mode.upper()}_{window}"
            df[ma_column_name] = ma_values
            # Pass the updated DataFrame and the new column name
            self.output_values['MA'] = (df, ma_column_name)
        except Exception as e:
            print(f"Node {self.id}: Error during MA calculation: {e}")
            self.output_values['MA'] = (None, None)

class MultiplyColumnNode(Node):
    def execute(self):
        # Retrieve input data
        input_slot = 0  # Assuming the input is always at slot 0
        if input_slot in self.input_connections:
            origin_node, origin_slot = self.input_connections[input_slot]
            output_name = origin_node.outputs[origin_slot]['name']
            input_data = origin_node.output_values.get(output_name)
        else:
            logging.warning(f"MultiplyColumnNode {self.id}: No input data.")
            self.output_values['Result'] = (None, None)
            return

        if input_data is None or input_data[0] is None:
            logging.warning(f"MultiplyColumnNode {self.id}: Input data is None.")
            self.output_values['Result'] = (None, None)
            return

        df, column_name = input_data

        if df is None or column_name is None:
            logging.warning(f"MultiplyColumnNode {self.id}: DataFrame or column name is None.")
            self.output_values['Result'] = (None, None)
            return

        # Validate 'factor'
        try:
            factor = float(self.properties.get('factor', 1.0))
            if not (0.000 <= factor <= 100.0):
                raise ValueError(f"'factor' {factor} is out of bounds [0.000, 100.000].")
        except (ValueError, TypeError) as e:
            logging.error(f"MultiplyColumnNode {self.id}: Invalid 'factor' value: {e}")
            self.output_values['Result'] = (df, None)
            return

        # Perform multiplication
        try:
            new_column_name = f"{column_name}_x_{factor}"
            df[new_column_name] = df[column_name] * factor
            logging.debug(f"MultiplyColumnNode {self.id}: Created new column '{new_column_name}'.")
            # Set the output
            self.output_values['Result'] = (df, new_column_name)
        except Exception as e:
            logging.error(f"MultiplyColumnNode {self.id}: Error during multiplication: {e}")
            self.output_values['Result'] = (None, None)


class VizualizeDataNode(Node):
    def execute(self):
        # Initialize a set of columns to keep, starting with the fixed columns
        columns_to_keep = ['date', 'open', 'high', 'low', 'close']

        base_df = None  # Initialize the base DataFrame

        # Loop through all inputs to add relevant columns to the list and merge DataFrames
        for input_slot, (origin_node, origin_slot) in self.input_connections.items():
            output_name = origin_node.outputs[origin_slot]['name']
            input_data = origin_node.output_values.get(output_name)
            print(f"Input Data for slot {input_slot}: {input_data}")

            if input_data is None or input_data[0] is None:
                print(f"VizualizeDataNode {self.id}: Input data is None for input slot {input_slot}")
                continue

            df, column_name = input_data
            if df is None or column_name is None:
                print(f"VizualizeDataNode {self.id}: DataFrame or column name is None for input slot {input_slot}")
                continue

            # Add the column to the list of columns to keep
            columns_to_keep.append(column_name)

            if base_df is None:
                # Set the first valid DataFrame as the base
                base_df = df.copy()
                print(f"VizualizeDataNode {self.id}: Base DataFrame set with columns {base_df.columns.tolist()}")
            else:
                # Merge the current DataFrame with the base DataFrame on 'date'
                try:
                    base_df = base_df.merge(df[['date', column_name]], on='date', how='left')
                    print(f"VizualizeDataNode {self.id}: Merged column '{column_name}' into base DataFrame.")
                except KeyError as e:
                    print(f"VizualizeDataNode {self.id}: Error merging DataFrame on 'date': {e}")
                    continue

        # Check if a base DataFrame exists after processing all inputs
        if base_df is None:
            print(f"VizualizeDataNode {self.id}: No valid input DataFrame found.")
            self.output_values['Filtered DataFrame'] = None
            return

        # Ensure all required columns are present
        missing_columns = [col for col in columns_to_keep if col not in base_df.columns]
        if missing_columns:
            print(f"VizualizeDataNode {self.id}: Missing columns after merge: {missing_columns}")
            # Depending on requirements, you might want to add these columns with default values
            for col in missing_columns:
                base_df[col] = None  # or some default value
            print(f"VizualizeDataNode {self.id}: Added missing columns with default values.")

        # Filter the base DataFrame to only keep the necessary columns
        try:
            df_filtered = base_df[columns_to_keep]
            print(f"VizualizeDataNode {self.id}: Filtered DataFrame with columns {df_filtered.columns.tolist()}:")
            print(df_filtered)
            self.output_values['Filtered DataFrame'] = df_filtered  # Store the filtered DataFrame as output
        except KeyError as e:
            print(f"VizualizeDataNode {self.id}: Error filtering DataFrame columns: {e}")
            self.output_values['Filtered DataFrame'] = None


class HeikinAshiNode(Node):
    def execute(self):
        # Retrieve input data for OHLC
        inputs = {}
        input_names = ['Open', 'High', 'Low', 'Close']
        input_slots = [0, 1, 2, 3]  # Assuming these are the input slots

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
                        print(f"HeikinAshiNode {self.id}: Column {column_name} not found in data.")
                        inputs[name] = None
                else:
                    print(f"HeikinAshiNode {self.id}: Input {name} data is None.")
                    inputs[name] = None
            else:
                print(f"HeikinAshiNode {self.id}: Input {name} not connected.")
                inputs[name] = None

        # Check that all inputs are present
        if not all([inputs.get('Open') is not None, inputs.get('High') is not None,
                    inputs.get('Low') is not None, inputs.get('Close') is not None]):
            print(f"HeikinAshiNode {self.id}: Missing input data.")
            # Set outputs to None
            self.output_values['HA_Open'] = (None, None)
            self.output_values['HA_High'] = (None, None)
            self.output_values['HA_Low'] = (None, None)
            self.output_values['HA_Close'] = (None, None)
            return

        # Assuming all inputs come from the same DataFrame, retrieve the base DataFrame
        # Here, we take the 'date' from one of the inputs
        origin_node, origin_slot = self.input_connections[0]
        base_df, _ = origin_node.output_values.get(origin_node.outputs[origin_slot]['name'])

        if base_df is None:
            print(f"HeikinAshiNode {self.id}: Base DataFrame is None.")
            self.output_values['HA_Open'] = (None, None)
            self.output_values['HA_High'] = (None, None)
            self.output_values['HA_Low'] = (None, None)
            self.output_values['HA_Close'] = (None, None)
            return

        # Calculate Heikin Ashi using pandas_ta
        try:
            df_ha = ta.ha(inputs['Open'], inputs['High'], inputs['Low'], inputs['Close'])
            # Add Heikin Ashi columns to the existing DataFrame
            base_df['HA_Open'] = df_ha['HA_open']
            base_df['HA_High'] = df_ha['HA_high']
            base_df['HA_Low'] = df_ha['HA_low']
            base_df['HA_Close'] = df_ha['HA_close']

            # Set outputs
            self.output_values['HA_Open'] = (base_df, 'HA_Open')
            self.output_values['HA_High'] = (base_df, 'HA_High')
            self.output_values['HA_Low'] = (base_df, 'HA_Low')
            self.output_values['HA_Close'] = (base_df, 'HA_Close')

            logging.info(f"HeikinAshiNode {self.id}: Successfully calculated and added Heikin Ashi columns.")
        except Exception as e:
            logging.error(f"HeikinAshiNode {self.id}: Error during Heikin Ashi calculation: {e}")
            self.output_values['HA_Open'] = (None, None)
            self.output_values['HA_High'] = (None, None)
            self.output_values['HA_Low'] = (None, None)
            self.output_values['HA_Close'] = (None, None)

class ComparaisonNode(Node):
    def execute(self):
        # Retrieve input data for two columns
        inputs = {}
        input_slots = [0, 1]  # Assuming these are the input slots for the two columns
        input_names = ['First Input', 'Second Input']

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
                        logging.warning(f"ComparaisonNode {self.id}: Column '{column_name}' not found in data.")
                        inputs[name] = None
                else:
                    logging.warning(f"ComparaisonNode {self.id}: Input '{name}' data is None.")
                    inputs[name] = None
            else:
                logging.warning(f"ComparaisonNode {self.id}: Input '{name}' not connected.")
                inputs[name] = None

        # Check that both inputs are present
        if inputs['First Input'] is None or inputs['Second Input'] is None:
            logging.warning(f"ComparaisonNode {self.id}: Missing input data.")
            self.output_values['bool_column'] = (None, None)
            return

        # Get the comparison operator from the node properties
        comparison_operator = self.properties.get('operator', '==')

        # Perform the comparison based on the selected operator
        comparison_result = None
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
                logging.warning(f"ComparaisonNode {self.id}: Unsupported comparison operator '{comparison_operator}'.")
                self.output_values['bool_column'] = (None, None)
                return
        except Exception as e:
            logging.error(f"ComparaisonNode {self.id}: Error during comparison: {e}")
            self.output_values['bool_column'] = (None, None)
            return

        # **Important Change: Do NOT modify the original DataFrame in place**
        # Instead, create a new DataFrame to hold the boolean column
        origin_node, origin_slot = self.input_connections[0]
        base_df, _ = origin_node.output_values.get(origin_node.outputs[origin_slot]['name'])

        if base_df is None:
            logging.error(f"ComparaisonNode {self.id}: Base DataFrame is None.")
            self.output_values['bool_column'] = (None, None)
            return

        # Create a new DataFrame copy to avoid modifying the original
        new_df = base_df.copy()

        # Create the bool column name based on the comparison operator
        bool_column_name = f"bool_{comparison_operator.replace(' ', '_')}"
        new_df[bool_column_name] = comparison_result

        # Set outputs
        self.output_values['bool_column'] = (new_df, bool_column_name)
        logging.info(f"ComparaisonNode {self.id}: Successfully created comparison column '{bool_column_name}'.")


def pve(graph_json):
    # Load JSON data (adjusted dates and symbols)
    data = json.loads(graph_json)

    # Build nodes and connections
    nodes = build_nodes(data['nodes'])
    build_connections(data['links'], nodes)

    # Build graph and in-degree
    graph, in_degree = build_graph(nodes)

    # Determine execution order
    sorted_node_ids = topological_sort(nodes, graph, in_degree)

    # Execute nodes
    execute_graph(sorted_node_ids, nodes)

    for node_id in sorted_node_ids:
        node = nodes[node_id]
        print(f"Node {node_id} outputs:")
        for output_name, output_value in node.output_values.items():
            print(f"  {output_name}:")
            if output_value is not None:
                if isinstance(output_value, tuple):
                    df, column_name = output_value
                    if df is not None and column_name is not None:
                        # print(df[column_name].head(50))
                        print(df)
                        for col in df.columns:
                            print(col)
                        return df
                    elif df is not None and column_name is None:
                        print("Column name is None")
                    else:
                        print("DataFrame is None")
                elif isinstance(output_value, pd.DataFrame):
                    # print(output_value.head(50))
                    print('idk what to write here')
                else:
                    print(f"Unsupported output value type: {type(output_value)}")
            else:
                print("No data")


# if __name__ == "__main__":
#     graph_json = '''
#
#     {"extra": {}, "links": [[3, 5, 0, 3, 0, "column"], [4, 5, 3, 4, 0, "column"], [5, 3, 0, 6, 0, "column"]], "nodes": [{"id": 5, "pos": [265, 126], "mode": 0, "size": {"0": 210, "1": 138}, "type": "custom/getdata", "flags": {}, "order": 0, "outputs": [{"name": "open", "type": "column", "links": [3], "slot_index": 0}, {"name": "high", "type": "column", "links": null}, {"name": "low", "type": "column", "links": null}, {"name": "close", "type": "column", "links": [4], "slot_index": 3}, {"name": "volume", "type": "column", "links": null}], "properties": {"symbol": "ETHUSDT", "endDate": "2024/10/02", "startDate": "2024/09/27"}}, {"id": 4, "pos": [572, 238], "mode": 0, "size": {"0": 210, "1": 58}, "type": "custom/indicators/ma", "flags": {}, "order": 2, "inputs": [{"link": 4, "name": "Close", "type": "column"}], "outputs": [{"name": "MA", "type": "column", "links": null}], "properties": {"mode": "ema", "windows": 7}}, {"id": 3, "pos": [604, 129], "mode": 0, "size": {"0": 210, "1": 58}, "type": "custom/indicators/ma", "flags": {}, "order": 1, "inputs": [{"link": 3, "name": "Close", "type": "column"}], "outputs": [{"name": "MA", "type": "column", "links": [5], "slot_index": 0}], "properties": {"mode": "sinwma", "windows": 7}}, {"id": 6, "pos": [852, 159], "mode": 0, "size": {"0": 210, "1": 58}, "type": "custom/indicators/ma", "flags": {}, "order": 3, "inputs": [{"link": 5, "name": "Close", "type": "column"}], "outputs": [{"name": "MA", "type": "column", "links": null}], "properties": {"mode": "rma", "windows": 7}}], "config": {}, "groups": [], "version": 0.4, "last_link_id": 5, "last_node_id": 6}
#
#                 '''
#     pve(graph_json)
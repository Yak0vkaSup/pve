# app/nodes/nodes.py
import logging
import pandas as pd
import pandas_ta as ta
import json
import time
from flask import current_app
import asyncio
import telegram
from .backtest import backtest, Bybit
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
    multiply_column,
    ma,
    super_trend,
)

# Configure logging for this module
logger = logging.getLogger(__name__)

class Node:
    df = None
    symbol = None
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

    @classmethod
    def set_symbol(cls, symbol):
        cls.symbol = symbol

    @classmethod
    def get_symbol(cls):
        return cls.symbol

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

class GetCloseNode(Node):
    def execute(self):
        df = Node.get_df()
        if df is not None:
            close_series = get_close(df)
            self.output_values['close'] = close_series
            logger.info(f"GetCloseNode {self.id}: Output 'close' set.")
        else:
            logger.error(f"GetCloseNode {self.id}: DataFrame is None.")
            self.output_values['close'] = None

class GetHighNode(Node):
    def execute(self):
        df = Node.get_df()
        if df is not None:
            high_series = get_high(df)
            self.output_values['high'] = high_series
            logger.info(f"GetHighNode {self.id}: Output 'high' set.")
        else:
            logger.error(f"GetHighNode {self.id}: DataFrame is None.")
            self.output_values['high'] = None

class GetLowNode(Node):
    def execute(self):
        df = Node.get_df()
        if df is not None:
            low_series = get_low(df)
            self.output_values['low'] = low_series
            logger.info(f"GetLowNode {self.id}: Output 'low' set.")
        else:
            logger.error(f"GetLowNode {self.id}: DataFrame is None.")
            self.output_values['low'] = None

class GetVolumeNode(Node):
    def execute(self):
        df = Node.get_df()
        if df is not None:
            volume_series = get_volume(df)
            self.output_values['volume'] = volume_series
            logger.info(f"GetVolumeNode {self.id}: Output 'volume' set.")
        else:
            logger.error(f"GetVolumeNode {self.id}: DataFrame is None.")
            self.output_values['volume'] = None

class GetLastValueNode(Node):
    def execute(self):
        series = self.input_values.get(0)  # Input series (pd.Series)

        if series is None or not isinstance(series, pd.Series):
            logger.error(f"GetLastValueNode {self.id}: Input is not a valid pandas Series.")
            self.output_values['Value'] = None
            return

        try:
            # Retrieve the second-to-last value
            if len(series) < 2:
                logger.error(f"GetLastValueNode {self.id}: Series is too short to retrieve the last completed value.")
                self.output_values['Value'] = None
                return

            last_value = series.iloc[-2]  # Second-to-last value (last completed time point)
            self.output_values['Value'] = last_value
            logger.info(f"GetLastValueNode {self.id}: Successfully retrieved last completed value: {last_value}.")
        except Exception as e:
            logger.error(f"GetLastValueNode {self.id}: Error retrieving last value: {e}")
            self.output_values['Value'] = None

class SetFloatNode(Node):
    def execute(self):
        float_value = self.properties.get('value', 1.0)
        logger.info(f"SetFloatNode {self.id}: Set float value to {float_value}.")
        self.output_values['Float'] = float_value

class SetIntegerNode(Node):
    def execute(self):
        integer_value = self.properties.get('value', 3)
        logger.info(f"SetIntegerNode {self.id}: Set integer value to {integer_value}.")
        self.output_values['Integer'] = integer_value

class SetStringNode(Node):
    def execute(self):
        string_value = self.properties.get('value', '')
        logger.info(f"SetStringNode {self.id}: Set string value to '{string_value}'.")
        self.output_values['String'] = string_value

class MultiplyColumnNode(Node):
    def execute(self):

        source_column = self.input_values.get(0)
        factor = self.input_values.get(1)

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

class MANode(Node):
    def execute(self):
        source_column = self.input_values.get(0)
        window = self.input_values.get(1)
        type = self.properties.get('ma_type', 'ema')
        if source_column is None:
            logger.error(f"EMANode {self.id}: Source column is None.")
            self.output_values['MA'] = None
            self.output_values['Default name'] = None
            return

        if window is None:
            logger.error(f"EMANode {self.id}: Window is None.")
            self.output_values['MA'] = None
            self.output_values['Default name'] = None
            return

        try:
            ma_series = ma(type, source_column, window)
            self.output_values['MA'] = ma_series
            self.output_values['Default name'] = type + '_' + str(window) + '_' + str(source_column.name)
            logger.info(f"MANode {self.id}: {type} column '{source_column.name}' with {window}.")
        except Exception as e:
            logger.error(f"MANode {self.id}: {e}")
            self.output_values['MA'] = None

class SuperTrendNode(Node):
    def execute(self):
        high = self.input_values.get(0)
        low = self.input_values.get(1)
        close = self.input_values.get(2)
        window = self.input_values.get(3)

        if high is None or low is None or close is None:
            logger.error(f"SuperTrendNode {self.id}: Source column is None.")
            self.output_values['SuperTrend'] = None  # Changed 'Result' to 'EMA'
            return

        if window is None:
            logger.error(f"SuperTrendNode {self.id}: Window is None.")
            self.output_values['SuperTrend'] = None  # Changed 'Result' to 'EMA'
            return

        try:
            supertrend_series = super_trend(high, low, close, window)
            self.output_values['SuperTrend'] = supertrend_series  # Changed 'Result' to 'EMA'
            logger.info(f"SuperTrendNode {self.id}: SuperTrend column with {window}.")
        except Exception as e:
            logger.error(f"EMANode {self.id}: {e}")
            self.output_values['SuperTrend'] = None  # Changed 'Result' to 'EMA'



class AddColumnNode(Node):
    def execute(self):
        df = Node.get_df()
        if df is not None:

            source_series = self.input_values.get(0)
            column_name = self.input_values.get(1)

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

class CrossOverNode(Node):
    def execute(self):
        column_a = self.input_values.get(0)  # First input column
        column_b = self.input_values.get(1)  # Second input column

        if column_a is None or column_b is None:
            logger.error(f"CrossOverNode {self.id}: One or both input columns are None.")
            self.output_values['Condition'] = None
            return

        try:
            # Check if column_a crosses over column_b (previously less, now greater)
            condition = (column_a.shift(1) < column_b.shift(1)) & (column_a > column_b)
            self.output_values['Condition'] = condition
            logger.info(f"CrossOverNode {self.id}: Successfully computed crossover condition.")
        except Exception as e:
            logger.error(f"CrossOverNode {self.id}: Error computing crossover condition: {e}")
            self.output_values['Condition'] = None


class EqualNode(Node):
    def execute(self):
        column_a = self.input_values.get(0)  # First input column
        column_b = self.input_values.get(1)  # Second input column

        if column_a is None or column_b is None:
            logger.error(f"EqualNode {self.id}: One or both input columns are None.")
            self.output_values['Condition'] = None
            return

        try:
            # Check if column_a is equal to column_b
            condition = column_a == column_b
            self.output_values['Condition'] = condition
            logger.info(f"EqualNode {self.id}: Successfully computed equality condition.")
        except Exception as e:
            logger.error(f"EqualNode {self.id}: Error computing equality condition: {e}")
            self.output_values['Condition'] = None


class AddConditionNode(Node):
    def execute(self):
        condition = self.input_values.get(0)  # Input condition
        condition_name = self.input_values.get(1)  # Input for condition name

        if condition is None:
            logger.error(f"AddConditionNode {self.id}: Condition is None.")
            return

        if condition_name is None:
            logger.error(f"AddConditionNode {self.id}: Condition name is None.")
            return

        try:
            # Add condition to the global DataFrame with the given name
            df = Node.get_df()
            if df is not None:
                updated_df = df.copy()
                condition_name = '$' + condition_name
                updated_df[condition_name] = condition
                Node.set_df(updated_df)
                logger.info(f"AddConditionNode {self.id}: Successfully added condition '{condition_name}'.")
            else:
                logger.error(f"AddConditionNode {self.id}: DataFrame is None.")
        except Exception as e:
            logger.error(f"AddConditionNode {self.id}: Error adding condition: {e}")


class GetConditionNode(Node):
    def execute(self):
        condition_name = self.input_values.get(0)  # Input for condition name

        if condition_name is None:
            logger.error(f"GetConditionNode {self.id}: Condition name is None.")
            self.output_values['Condition'] = None
            return

        try:
            # Retrieve condition from the global DataFrame by name
            df = Node.get_df()
            if df is not None and condition_name in df:
                condition_name = '$' + condition_name
                self.output_values['Condition'] = df[condition_name]
                logger.info(f"GetConditionNode {self.id}: Successfully retrieved condition '{condition_name}'.")
            else:
                logger.error(f"GetConditionNode {self.id}: Condition '{condition_name}' not found in DataFrame.")
                self.output_values['Condition'] = None
        except Exception as e:
            logger.error(f"GetConditionNode {self.id}: Error retrieving condition: {e}")
            self.output_values['Condition'] = None

class GetColumnNode(Node):
    def execute(self):
        column_name = self.input_values.get(0)  # Input for column name

        if column_name is None:
            logger.error(f"GetColumnNode {self.id}: Column name is None.")
            self.output_values['Column'] = None
            return

        try:
            # Retrieve the column from the global DataFrame by name
            df = Node.get_df()
            if df is not None and column_name in df.columns:
                self.output_values['Column'] = df[column_name]
                logger.info(f"GetColumnNode {self.id}: Successfully retrieved column '{column_name}'.")
            else:
                logger.error(f"GetColumnNode {self.id}: Column '{column_name}' not found in DataFrame.")
                self.output_values['Column'] = None
        except Exception as e:
            logger.error(f"GetColumnNode {self.id}: Error retrieving column: {e}")
            self.output_values['Column'] = None


class SmallerNode(Node):
    def execute(self):
        column_a = self.input_values.get(0)  # First input column
        column_b = self.input_values.get(1)  # Second input column

        if column_a is None or column_b is None:
            logger.error(f"SmallerNode {self.id}: One or both input columns are None.")
            self.output_values['Condition'] = None
            return

        try:
            # Check if column_a is smaller than column_b
            condition = column_a < column_b
            self.output_values['Condition'] = condition
            logger.info(f"SmallerNode {self.id}: Successfully computed smaller condition.")
        except Exception as e:
            logger.error(f"SmallerNode {self.id}: Error computing smaller condition: {e}")
            self.output_values['Condition'] = None
class OrNode(Node):
    def execute(self):
        condition_a = self.input_values.get(0)  # First input condition
        condition_b = self.input_values.get(1)  # Second input condition

        if condition_a is None or condition_b is None:
            logger.error(f"OrNode {self.id}: One or both input conditions are None.")
            self.output_values['Condition'] = None
            return

        try:
            # Perform logical OR operation
            result = condition_a | condition_b
            self.output_values['Condition'] = result
            logger.info(f"OrNode {self.id}: Successfully computed OR condition.")
        except Exception as e:
            logger.error(f"OrNode {self.id}: Error computing OR condition: {e}")
            self.output_values['Condition'] = None


class AndNode(Node):
    def execute(self):
        condition_a = self.input_values.get(0)  # First input condition
        condition_b = self.input_values.get(1)  # Second input condition

        if condition_a is None or condition_b is None:
            logger.error(f"AndNode {self.id}: One or both input conditions are None.")
            self.output_values['Condition'] = None
            return

        try:
            # Perform logical AND operation
            result = condition_a & condition_b
            self.output_values['Condition'] = result
            logger.info(f"AndNode {self.id}: Successfully computed AND condition.")
        except Exception as e:
            logger.error(f"AndNode {self.id}: Error computing AND condition: {e}")
            self.output_values['Condition'] = None


class NotNode(Node):
    def execute(self):
        condition = self.input_values.get(0)  # Input condition

        if condition is None:
            logger.error(f"NotNode {self.id}: Input condition is None.")
            self.output_values['Condition'] = None
            return

        try:
            # Perform logical NOT operation
            result = ~condition
            self.output_values['Condition'] = result
            logger.info(f"NotNode {self.id}: Successfully computed NOT condition.")
        except Exception as e:
            logger.error(f"NotNode {self.id}: Error computing NOT condition: {e}")
            self.output_values['Condition'] = None

class IfNode(Node):
    def execute(self):
        condition_series = self.input_values.get(0)  # Input condition (pd.Series of boolean values)

        if condition_series is None or not isinstance(condition_series, pd.Series):
            logger.error(f"IfNode {self.id}: Condition is not a valid pandas Series.")
            self.output_values['True'] = None
            self.output_values['False'] = None
            return

        try:
            # Retrieve the last completed minute's value (second-to-last index in the series)
            if len(condition_series) < 2:
                logger.error(f"IfNode {self.id}: Condition Series is too short to evaluate.")
                self.output_values['True'] = None
                self.output_values['False'] = None
                return

            last_value = condition_series.iloc[-2]  # Second-to-last value (last completed minute)

            if last_value:
                logger.info(f"IfNode {self.id}: Last completed condition evaluated to True.")
                self.output_values['True'] = True  # Execution flow for True branch
                self.output_values['False'] = None
            else:
                logger.info(f"IfNode {self.id}: Last completed condition evaluated to False.")
                self.output_values['True'] = None
                self.output_values['False'] = True  # Execution flow for False branch
        except Exception as e:
            logger.error(f"IfNode {self.id}: Error evaluating condition: {e}")
            self.output_values['True'] = None
            self.output_values['False'] = None

class SendMessageNode(Node):
    def execute(self):
        exec = self.input_values.get(0)
        message = self.input_values.get(1)  # Input message
        user_id = self.input_values.get(2)  # Input user ID

        if exec is None:
            logger.info(f"SendMessageNode {self.id}: Condition not met, stop of execution.")
            return

        if message is None or user_id is None:
            logger.error(f"SendMessageNode {self.id}: Message or UserID is None.")
            return

        try:
            # Retrieve the bot token from the app configuration
            bot_token = current_app.config['TELEGRAM_BOT_TOKEN']
            bot = telegram.Bot(bot_token)

            # Send the message to the user
            asyncio.run(bot.send_message(chat_id=user_id, text=message))
            logger.info(f"SendMessageNode {self.id}: Message successfully sent to user {user_id}.")
            self.output_values['Exec'] = True
        except Exception as e:
            logger.error(f"SendMessageNode {self.id}: Error sending message: {e}")
            self.output_values['Exec'] = None

class SimpleBacktestNode(Node):
    def execute(self):
        # Retrieve input values
        inputs = {
            "signals": self.input_values.get(0),
            "profit_target": self.input_values.get(1),
            "num_orders": self.input_values.get(2),
            "martingale_factor": self.input_values.get(3),
            "candles_to_close": self.input_values.get(4),
            "step_percentage": self.input_values.get(5),
            "first_order_size": self.input_values.get(6),
        }

        # Validate all inputs
        missing_inputs = [key for key, value in inputs.items() if value is None]
        if missing_inputs:
            logger.error(f"SimpleBacktestNode {self.id}: Missing inputs: {', '.join(missing_inputs)}.")
            return

        if not isinstance(inputs["signals"], pd.Series):
            logger.error(f"SimpleBacktestNode {self.id}: Signals must be a pandas Series.")
            return

        # Retrieve DataFrame and symbol
        df, symbol = Node.get_df(), Node.get_symbol()
        if df is None or symbol is None:
            logger.error(f"SimpleBacktestNode {self.id}: Missing DataFrame or symbol.")
            return

        try:
            # Run backtest with configuration
            config = {
                "profit_target": inputs["profit_target"],
                "first_order_size_usdt": inputs["first_order_size"],
                "step_percentage": inputs["step_percentage"],
                "num_orders": inputs["num_orders"],
                "martingale_factor": inputs["martingale_factor"],
                "candles_to_close": inputs["candles_to_close"],
            }
            bybit = Bybit("", "")  # Replace with actual credentials
            pve = backtest(df, inputs["signals"], symbol, bybit, config)

            # Log and output the backtest result
            logger.info(f"SimpleBacktestNode {self.id}: Backtest executed successfully.")
            self.output_values["Backtest Result"] = pve
        except Exception as e:
            logger.error(f"SimpleBacktestNode {self.id}: Error executing backtest: {e}")

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
        elif node_type == 'get/close':
            node = GetCloseNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'get/high':
            node = GetHighNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'get/low':
            node = GetLowNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'get/volume':
            node = GetVolumeNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'get/last_value':
            node = GetLastValueNode(node_id, node_type, properties, inputs, outputs)

        elif node_type == 'math/multiply_column':
            node = MultiplyColumnNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'set/float':
            node = SetFloatNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'set/string':
            node = SetStringNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'set/integer':
            node = SetIntegerNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'indicators/ma':
            node = MANode(node_id, node_type, properties, inputs, outputs)

        elif node_type == 'compare/cross_over':
            node = CrossOverNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'compare/equal':
            node = EqualNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'compare/smaller':
            node = SmallerNode(node_id, node_type, properties, inputs, outputs)

        elif node_type == 'tools/add_column':
            node = AddColumnNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'tools/get_condition':
            node = GetConditionNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'tools/get_column':
            node = GetColumnNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'tools/add_condition':
            node = AddConditionNode(node_id, node_type, properties, inputs, outputs)

        elif node_type == 'logic/and':
            node = AndNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'logic/or':
            node = OrNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'logic/not':
            node = NotNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'logic/if':
            node = IfNode(node_id, node_type, properties, inputs, outputs)

        elif node_type == 'telegram/send_message':
            node = SendMessageNode(node_id, node_type, properties, inputs, outputs)

        elif node_type == 'backtest/simple_backtest':
            node = SimpleBacktestNode(node_id, node_type, properties, inputs, outputs)

        else:
            logger.error(f"Unknown node type: {node_type}")
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


def process_graph(graph_json, start_date, end_date, symbol, timeframe):
    logger.info("Starting graph processing")
    start_time = time.time()
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

    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)

    # And here we need to resample it based on timeframe
    df_resampled = df.resample(timeframe).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
    })

    df_resampled.reset_index(inplace=True)

    Node.set_df(df_resampled)
    Node.set_symbol(symbol)

    nodes = build_nodes(data['nodes'])
    build_connections(data['links'], nodes)

    graph, in_degree = build_graph(nodes)
    sorted_node_ids = topological_sort(nodes, graph, in_degree)
    logger.info(f"Execution order: {sorted_node_ids}")

    execute_graph(sorted_node_ids, nodes)

    final_df = Node.get_df()
    # final_df.to_csv('test_out.csv', index=False)


    if final_df is not None:
        logger.info("Processing complete. Retrieved final Data...")
    else:
        logger.error("No valid output DataFrame found after processing")

    end_time = time.time()
    execution_time = (end_time - start_time) * 1000
    logger.info(f"Execution time: {execution_time} ms")
    return final_df
# app/routes/graph_routes.py
from flask import Blueprint, request, jsonify, current_app
from ..utils.token_utils import token_required
from ..models.graph_model import Graph
from ..utils.logger import log_request
from ..nodes.nodes import process_graph
from ..socketio_setup import socketio
import json
import logging
import pandas as pd
import threading

graph_bp = Blueprint('graph_bp', __name__)

@graph_bp.route('/api/save-graph', methods=['POST'])
@log_request
@token_required
def save_graph():
    try:
        request_data = request.get_json()
        user_id = request_data.get('user_id')
        graph_name = request_data.get('name')
        graph_data = request_data.get('graph_data')
        start_date = request_data.get('start_date')
        end_date = request_data.get('end_date')
        symbol = request_data.get('symbol')
        timeframe = request_data.get('timeframe')

        if isinstance(graph_data, dict):
            graph_json = json.dumps(graph_data)
        else:
            graph_json = graph_data
        Graph.save_or_update(user_id, graph_name, graph_json, start_date, end_date, symbol, timeframe)
        return jsonify({'status': 'success', 'message': 'Graph saved successfully'})
    except Exception as e:
        current_app.logger.error(f"Error saving graph: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@graph_bp.route('/api/delete-graph', methods=['POST'])
@log_request
@token_required
def delete_graph():
    try:
        request_data = request.get_json()
        user_id = request_data.get('user_id')
        graph_name = request_data.get('name')
        Graph.delete(user_id, graph_name)
        return jsonify({'status': 'success', 'message': 'Graph saved successfully'})
    except Exception as e:
        current_app.logger.error(f"Error saving graph: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@graph_bp.route('/api/get-saved-graphs', methods=['GET'])
@log_request
@token_required
def get_saved_graphs():
    try:
        user_id = request.args.get('id')
        graphs = Graph.get_all_by_user(user_id)
        return jsonify({'status': 'success', 'graphs': graphs})
    except Exception as e:
        current_app.logger.error(f"Error fetching graphs: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@graph_bp.route('/api/load-graph', methods=['POST'])
@log_request
@token_required
def load_graph():
    try:
        request_data = request.get_json()
        user_id = request_data.get('user_id')
        graph_name = request_data.get('name')

        graph_record = Graph.load(user_id, graph_name)

        if not graph_record:
            return jsonify({'status': 'error', 'message': 'Graph not found'}), 404

        graph_data, start_date, end_date, symbol, timeframe = graph_record
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()

        response_payload = {
            'status': 'success',
            'graph_data': graph_data,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'symbol': symbol,
            'timeframe': timeframe
        }
        return jsonify(response_payload)
    except Exception as e:
        current_app.logger.error(f"Error loading graph: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

thread_local = threading.local()
class LogCaptureHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            user_id = getattr(thread_local, 'user_id', None)
            if user_id:
                socketio.emit('log_message', {'message': msg}, to=user_id)
        except Exception:
            self.handleError(record)

@graph_bp.route('/api/compile-graph', methods=['POST'])
@log_request
@token_required
def compile_graph():
    try:
        request_data = request.get_json()
        user_id = request_data.get('user_id')
        graph_name = request_data.get('name')

        graph_data = Graph.load(user_id, graph_name)

        if not graph_data:
            return jsonify({'status': 'error', 'message': 'Graph not found'}), 404

        graph = graph_data[0]
        start_date = graph_data[1]
        end_date = graph_data[2]
        symbol = graph_data[3]
        timeframe = graph_data[4]

        if isinstance(graph, dict):
            graph_json = json.dumps(graph)
        else:
            graph_json = graph

        # Set the user_id in thread-local storage
        thread_local.user_id = user_id

        # Set up the logging handler
        log_capture_handler = LogCaptureHandler()
        log_capture_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_capture_handler.setFormatter(formatter)

        # Get the logger and add the handler
        logger = logging.getLogger('app.nodes.nodes')
        logger.addHandler(log_capture_handler)

        df, precision, min_move = process_graph(graph_json, start_date, end_date, symbol, timeframe)

        logger.removeHandler(log_capture_handler)
        if hasattr(thread_local, 'user_id'):
            del thread_local.user_id

        if df is not None:
            df['date'] = df['date'].astype('int64') // 10 ** 9
            # df = df.fillna(value=0)
            # df = df.dropna(how='all', axis=1)

            columns_to_ignore = ['date', 'open', 'high', 'low', 'close', 'volume']
            ma_columns = [col for col in df.columns if col not in columns_to_ignore]
            df[ma_columns] = df[ma_columns].astype(object)

            # Replace NaN with None in the MA columns
            df[ma_columns] = df[ma_columns].where(pd.notna(df[ma_columns]), None)
            print(df.tail(50))
            data = df.to_dict('records')
            user_id=str(user_id)

            socketio.emit('update_chart', {
                'status': 'success',
                'data': data,
                'precision': precision,
                'minMove': min_move
            }, to=user_id, namespace='/')

            return jsonify({'status': 'success', 'message': 'Compiled and data sent to chart'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to process graph'}), 500
    except Exception as e:
        current_app.logger.error(f"Error compiling graph: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

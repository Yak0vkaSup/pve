# app/routes/graph_routes.py
import os
import uuid

from flask import Blueprint, request, jsonify, current_app, send_file, url_for
from ..utils.token_utils import token_required
from ..models.graph_model import Graph
from ..utils.logger import log_request, delete_file_after_delay, SocketIOLogHandler
from ..nodes.nodes import process_graph
from ..socketio_setup import socketio
from functools import wraps
import json
import logging
import pandas as pd
import threading
import io
import datetime
TEMP_DIR = "/backtest_files"

graph_bp = Blueprint('graph_bp', __name__)



def is_dev_mode():
    """Check if Flask is running in development mode."""
    return current_app.config.get('FLASK_ENV') == 'development'


def token_required(f):
    """Decorator to enforce authentication only in production mode."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if is_dev_mode():
            # Bypass authentication in development mode
            return f(*args, **kwargs)

        # Normal authentication process
        token = request.headers.get('Authorization')

        if not token:
            return jsonify({'status': 'error', 'message': 'Missing authentication token'}), 401

        # Perform token verification
        if not verify_token_logic(token):  # Replace with actual token verification function
            return jsonify({'status': 'error', 'message': 'Invalid or expired token'}), 403

        return f(*args, **kwargs)

    return decorated_function

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

        graph, start_date, end_date, symbol, timeframe = graph_data
        graph_json = json.dumps(graph) if isinstance(graph, dict) else graph

        # Set the user_id in thread-local storage
        thread_local.user_id = user_id

        # Get logger and attach our SocketIO handler
        logger = logging.getLogger('app.nodes.nodes')
        socket_handler = SocketIOLogHandler(user_id)
        socket_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        socket_handler.setFormatter(formatter)
        logger.addHandler(socket_handler)

        # Process graph
        df, precision, min_move = process_graph(graph_json, start_date, end_date, symbol, timeframe)

        # Remove handler and thread-local storage cleanup
        logger.removeHandler(socket_handler)
        if hasattr(thread_local, 'user_id'):
            del thread_local.user_id

        if df is not None:
            df['date'] = df['date'].astype('int64') // 10 ** 9

            # Process DataFrame
            columns_to_ignore = ['date', 'open', 'high', 'low', 'close', 'volume']
            ma_columns = [col for col in df.columns if col not in columns_to_ignore]
            df[ma_columns] = df[ma_columns].astype(object)
            df[ma_columns] = df[ma_columns].where(pd.notna(df[ma_columns]), None)

            # Generate a unique file name with timestamp
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            unique_id = str(uuid.uuid4())[:8]  # Short unique ID
            filename = f"{timestamp}_backtest_{unique_id}.csv"
            file_path = os.path.join(TEMP_DIR, filename)

            # Save CSV
            df.to_csv(file_path, index=False)
            logger.info(f"Saved file to: {file_path}")

            # Generate temporary link (force HTTPS)
            file_url = url_for('graph_bp.download_backtest', filename=filename, _external=True, _scheme='https')
            file_url = str(file_url).replace("http://", "https://")
            # Schedule file deletion after 5 minutes
            threading.Thread(target=delete_file_after_delay, args=(file_path, 300)).start()

            # Optionally, also send a log message with the link
            log_message = f"Backtest file available for 5 minutes: {file_url}"
            socketio.emit('log_message', {'message': log_message}, to=user_id)

            # Send chart update
            data = df.to_dict('records')
            socketio.emit('update_chart', {
                'status': 'success',
                'data': data,
                'precision': precision,
                'minMove': min_move
            }, to=str(user_id))

            return jsonify({'status': 'success', 'message': 'Compiled and data sent to chart'})

        else:
            return jsonify({'status': 'error', 'message': 'Failed to process graph'}), 500
    except Exception as e:
        current_app.logger.error(f"Error compiling graph: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@graph_bp.route('/api/download-backtest/<filename>', methods=['GET'])
def download_backtest(filename):
    """Serve the backtest CSV file if it exists."""
    file_path = os.path.join(TEMP_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, mimetype="text/csv", as_attachment=True, download_name=filename)
    else:
        return jsonify({'status': 'error', 'message': 'File expired or does not exist'}), 404

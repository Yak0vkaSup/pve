# app/routes/graph_routes.py
import os
import uuid
from flask import Blueprint, request, jsonify, current_app, send_file, url_for
from ..utils.token_utils import token_required
from ..models.graph_model import Graph
from ..utils.logger import log_request, delete_file_after_delay, SocketIOLogHandler
from ..utils.rate_limiter import rate_limit
from ..socketio_setup import socketio
import json
import logging
import pandas as pd
import threading
import io
import datetime

graph_bp = Blueprint('graph_bp', __name__)

def load_template_graph_for_user(user_id):
    """
    Loads ALL template graphs located in backend/template_graphs and saves them
    to the new user. Every template found (*.json) is saved as a graph under
    the user's account. After saving, each template is compiled once (via the
    Celery task) so the user immediately has ready-to-go strategies.

    Returns True if at least one template was processed successfully, False otherwise.
    """
    try:
        # Get the directory where this file is located
        current_dir = os.path.dirname(os.path.abspath(__file__))  # .../backend/pve/app/routes
        # Navigate up three levels to reach the backend directory
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))  # .../backend
        template_dir = os.path.join(backend_dir, 'template_graphs')

        if not os.path.exists(template_dir):
            current_app.logger.error(f"Template directory not found at: {template_dir}")
            return False

        from ..vpl.tasks import process_graph_task  # import here to avoid circular

        processed_any = False

        for fname in os.listdir(template_dir):
            if not fname.lower().endswith('.json'):
                continue  # skip non-json

            fpath = os.path.join(template_dir, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)

                graph_data = template_data.get('graph', {})
                start_date = template_data.get('startDate', '2024-01-01')
                end_date = template_data.get('endDate', '2024-01-04')
                symbol = template_data.get('symbol', 'BTCUSDT')
                timeframe = template_data.get('timeframe', '1h')

                # Determine graph name – prefer explicit name in JSON, else file name
                graph_name = template_data.get('graphName') or os.path.splitext(fname)[0].replace('_', ' ').title()

                graph_json = json.dumps(graph_data)

                Graph.save_or_update(user_id, graph_name, graph_json, start_date, end_date, symbol, timeframe)
                current_app.logger.info(f"Template graph '{graph_name}' saved for user {user_id}")

                # Kick off compilation (fire-and-forget)
                process_graph_task.delay(user_id, graph_name)

                processed_any = True
            except Exception as inner_e:
                current_app.logger.error(f"Failed to process template {fname}: {str(inner_e)}")
                continue

        return processed_any
        
    except Exception as e:
        current_app.logger.error(f"Error loading template graph for user {user_id}: {str(e)}")
        return False

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

@graph_bp.route('/api/create-empty-strategy', methods=['POST'])
@log_request
@token_required
def create_empty_strategy():
    try:
        request_data = request.get_json()
        user_id = request_data.get('user_id')
        graph_name = request_data.get('name')
        
        if not graph_name or not graph_name.strip():
            return jsonify({'status': 'error', 'message': 'Strategy name is required'}), 400
            
        new_id = Graph.create_empty(user_id, graph_name.strip())
        
        if new_id is None:
            return jsonify({'status': 'error', 'message': 'A strategy with this name already exists'}), 409
            
        return jsonify({'status': 'success', 'message': 'Empty strategy created successfully', 'id': new_id})
    except Exception as e:
        current_app.logger.error(f"Error creating empty strategy: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@graph_bp.route('/api/delete-graph', methods=['POST'])
@log_request
@token_required
def delete_graph():
    try:
        request_data = request.get_json()
        user_id = request_data.get('user_id')
        graph_id = request_data.get('strategy_id')
        
        if not graph_id:
            return jsonify({'status': 'error', 'message': 'Strategy ID is required'}), 400
            
        success = Graph.delete_by_id(user_id, graph_id)
        
        if success:
            return jsonify({'status': 'success', 'message': 'Strategy deleted successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Strategy not found or you do not have permission to delete it'}), 404
    except Exception as e:
        current_app.logger.error(f"Error deleting graph: {str(e)}")
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
@rate_limit(10)  # 30 seconds cooldown
@token_required
def compile_graph():
    from ..vpl.tasks import process_graph_task
    try:
        request_data = request.get_json()
        user_id = request_data.get('user_id')
        graph_name = request_data.get('name')

        task = process_graph_task.delay(user_id, graph_name)
        return jsonify({'status': 'success', 'message': 'Compilation started'})
    except Exception as e:
        current_app.logger.error(f"Error starting task: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# app/routes/graph_routes.py
from flask import Blueprint, request, jsonify, current_app
from ..utils.token_utils import token_required
from ..models.graph_model import Graph
from ..utils.logger import log_request
from ..nodes.nodes import process_graph
from ..socketio_setup import socketio
import json
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

        if isinstance(graph_data, dict):
            graph_json = json.dumps(graph_data)
        else:
            graph_json = graph_data
        Graph.save_or_update(user_id, graph_name, graph_json, start_date, end_date, symbol)
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
        print(graphs)
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

        graph_data, start_date, end_date, symbol = graph_record
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()

        response_payload = {
            'status': 'success',
            'graph_data': graph_data,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'symbol': symbol
        }
        return jsonify(response_payload)
    except Exception as e:
        current_app.logger.error(f"Error loading graph: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

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

        if isinstance(graph_data, dict):
            graph_json = json.dumps(graph_data)
        else:
            graph_json = graph_data

        df = process_graph(graph_json)
        if df is not None:
            df['date'] = df['date'].astype(int) // 10**9
            df = df.fillna(value=0)
            print(df.tail())
            data = df.to_dict('records')
            user_id=str(user_id)
            socketio.emit('update_chart', {'status': 'success', 'data': data}, to=user_id, namespace='/')
            return jsonify({'status': 'success', 'message': 'Compiled and data sent to chart'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to process graph'}), 500
    except Exception as e:
        current_app.logger.error(f"Error compiling graph: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

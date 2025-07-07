import os
import uuid
from flask import Blueprint, request, jsonify, current_app, send_file, url_for
from ..utils.token_utils import token_required
from ..utils.rate_limiter import rate_limit
from pve.app.models.backtest_model import BacktestResult
from pve.app.models.analizer_model import AnalyzerResult

backtest_bp = Blueprint('backtest_bp', __name__)

@backtest_bp.route('/api/get-backtests', methods=['GET'])
@token_required
def get_backtests():
    try:
        user_id = request.args.get('user_id')
        backtests = BacktestResult.get_all_by_user(user_id)
        response = jsonify({'status': 'success', 'backtests': backtests})
        # Disable caching so that a fresh response is always sent.
        response.headers['Cache-Control'] = 'no-store'
        return response
    except Exception as e:
        current_app.logger.error(f"Error fetching backtests: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@backtest_bp.route('/api/launch-analyzer', methods=['POST'])
@token_required
@rate_limit(30) 
def launch_analyzer():
    try:
        from ..vpl.tasks import process_analyzer_task
        request_data = request.get_json()
        user_id = request_data.get('user_id')
        backtest_id = request_data.get('backtest_id')
        initial_capital = request_data.get('initial_capital')
        # Launch the analyzer Celery task.
        process_analyzer_task.delay(user_id, backtest_id, initial_capital)
        return jsonify({'status': 'success', 'message': 'Analyzer task started'})
    except Exception as e:
        current_app.logger.error(f"Error launching analyzer: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

from pve.app.socketio_setup import socketio

@backtest_bp.route('/api/get-analyzer-result', methods=['GET'])
@token_required
def get_analyzer_result():
    try:
        user_id = request.args.get('user_id')
        backtest_id = request.args.get('backtest_id')
        backtest = BacktestResult.load_by_id(backtest_id)
        if not backtest or not backtest.get("analyzer_result_id"):
            return jsonify({'status': 'error', 'message': 'Analyzer result not found'}), 404
        analyzer_id = backtest.get("analyzer_result_id")
        analyzer_result = AnalyzerResult.load(user_id, analyzer_id)
        analyzer_result["timeframe"] = backtest["timeframe"]
        socketio.emit('update_chart', {
            'status': 'success',
            'data': backtest['backtest_data'],
            'precision': float(backtest['precision']),
            'minMove': float(backtest['min_move']),
            'orders': backtest['orders']
        }, to=str(user_id))

        return jsonify({'status': 'success', 'analyzer_result': analyzer_result})
    except Exception as e:
        current_app.logger.error(f"Error fetching analyzer result: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@backtest_bp.route('/api/get-backtest', methods=['GET'])
@token_required
def get_backtest():
    """
    Return the complete back-test record (including graph) by id.
    Required query params: user_id, backtest_id, token
    """
    try:
        user_id     = request.args.get('user_id')
        backtest_id = request.args.get('backtest_id')

        backtest = BacktestResult.load_by_id(backtest_id)
        if not backtest:
            return jsonify({'status': 'error', 'message': 'Backtest not found'}), 404

        # cheap ownership check – skip if you don’t need it
        if str(backtest.get('user_id', user_id)) != str(user_id):
            return jsonify({'status': 'error', 'message': 'Forbidden'}), 403

        return jsonify({'status': 'success', 'backtest': backtest})
    except Exception as e:
        current_app.logger.error(f"Error fetching backtest: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

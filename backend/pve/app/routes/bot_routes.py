from flask import Blueprint, request, jsonify, current_app
from ..utils.logger import log_request
from ..models.backtest_model import BacktestResult
from ..utils.token_utils import token_required, bot_owner_required
from ..models.bot_model import Bot
from ..utils.database import get_db_connection
import redis
import json

bot_bp = Blueprint('bot_bp', __name__)
redis_client = redis.Redis(host='redis', port=6379, db=0)
ALLOWED_DELETE_STATES = ('stopped', 'error', 'created', 'inactive')

@bot_bp.route('/api/bots', methods=['GET'])
@log_request
@token_required
def get_bots():
    """
    Get all bots for the authenticated user.
    """
    try:
        user_id = request.args.get('user_id')
        bots = Bot.get_all_by_user(user_id)
        return jsonify({'status': 'success', 'bots': bots})
    except Exception as e:
        current_app.logger.error(f"Error fetching bots: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bot_bp.route('/api/bots', methods=['POST'])
@log_request
@token_required
def create_bot():
    try:
        request_data = request.get_json()
        current_app.logger.info(f"Received payload: {request_data}")
        user_id = request_data.get('user_id')
        name = request_data.get('name')
        parameters = request_data.get('parameters')

        if not (user_id and name and parameters):
            return jsonify({'error': 'Missing required parameters'}), 400

        # ------------------------------------------------------------------
        # if the client sent only backtest_id, enrich the payload locally
        # ------------------------------------------------------------------
        backtest_id = parameters.get('backtest_id')
        if backtest_id:
            bt = BacktestResult.load_by_id(backtest_id)
            if bt:
                parameters.update({
                    'symbol': bt.get('symbol'),
                    'timeframe': bt.get('timeframe'),
                    'strategy': bt.get('graph_name'),
                    'vpl': bt.get('graph'),
                    'graph': bt.get('graph'),
                })

        bot_id = Bot.create(user_id, name, parameters)
        return jsonify({'status': 'success', 'bot_id': bot_id}), 201
    except Exception as e:
        current_app.logger.error(f"Error creating bot: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500



@bot_bp.route('/api/bots/<int:bot_id>/start', methods=['POST'])
@log_request
@token_required
@bot_owner_required
def start_bot(bot_id):
    """
    Start a bot.
    """
    try:
        Bot.update_status('to_be_launched', bot_id)

        redis_client.publish('bot-launch-channel', str(bot_id))

        return jsonify({'status': 'success', 'message': f'Bot {bot_id} is launching...'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bot_bp.route('/api/bots/<int:bot_id>/stop', methods=['POST'])
@log_request
@token_required
@bot_owner_required
def stop_bot(bot_id):
    """
    Stop a bot via Redis.
    """
    try:
        Bot.update_status('to_be_stopped', bot_id)

        redis_client.publish('bot-stop-channel', str(bot_id))

        return jsonify({'status': 'success', 'message': f'Bot {bot_id} is stopping...'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bot_bp.route('/api/bots/<int:bot_id>', methods=['DELETE'])
@log_request
@token_required
@bot_owner_required
def delete_bot(bot_id: int):
    """
    Permanently delete a bot *iff* it is not running.
    """
    try:
        deleted = Bot.delete(bot_id, request.user_id, ALLOWED_DELETE_STATES)
        if not deleted:
            return jsonify({'status': 'error',
                            'message': 'Bot must be stopped before deletion'}), 409
        return jsonify({'status': 'success', 'message': f'Bot {bot_id} deleted'})
    except Exception as e:
        current_app.logger.error("Error deleting bot: %s", e, exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

from pve.app.socketio_setup import socketio

@bot_bp.route('/api/bots/<int:bot_id>/pnl', methods=['GET'])
@log_request
@token_required
@bot_owner_required
def get_bot_pnl(bot_id):
    """
    Fetch closed PnL data for a bot using its API credentials.
    """
    current_app.logger.info(f"PnL endpoint called for bot {bot_id}")
    
    try:
        # Get optional parameters
        limit = int(request.args.get('limit', 50))
        cursor = request.args.get('cursor')
        
        current_app.logger.info(f"Fetching PnL for bot {bot_id}, limit: {limit}, cursor: {cursor}")
        
        # Use the Bot model method to get PnL data
        result = Bot.get_pnl_data(bot_id, limit, cursor)
        
        if result['status'] == 'success':
            return jsonify(result)
        else:
            status_code = 404 if 'not found' in result['message'].lower() else 400
            return jsonify(result), status_code
            
    except Exception as e:
        current_app.logger.error(f"Error fetching bot PnL: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bot_bp.route('/api/bots/<int:bot_id>/logs', methods=['GET'])
@log_request
@token_required
@bot_owner_required
def get_bot_logs(bot_id):
    """
    Fetch paginated logs for a bot.
    """
    current_app.logger.info(f"Logs endpoint called for bot {bot_id}")
    
    try:
        # Get optional parameters
        limit = int(request.args.get('limit', 50))
        cursor = request.args.get('cursor')
        
        current_app.logger.info(f"Fetching logs for bot {bot_id}, limit: {limit}, cursor: {cursor}")
        
        # Use the Bot model method to get paginated logs
        result = Bot.get_logs_paginated(bot_id, limit, cursor)
        
        if result['status'] == 'success':
            return jsonify(result)
        else:
            status_code = 404 if 'not found' in result['message'].lower() else 400
            return jsonify(result), status_code
            
    except Exception as e:
        current_app.logger.error(f"Error fetching bot logs: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bot_bp.route('/api/bots/<int:bot_id>/stats', methods=['GET'])
@log_request
@token_required
@bot_owner_required
def bot_stats(bot_id):
    """
    Return both the latest performance data and recent logs for a bot, *and*
    broadcast the dataframe so the GUI chart refreshes.
    """
    try:
        limit   = int(request.args.get('limit', 100))
        user_id = request.args.get('user_id')        # ← needed for socket room

        perf = Bot.get_performance(bot_id)
        logs = Bot.get_logs(bot_id, limit)

        # ------------- NEW: push the DF to the chart ------------------
        if perf and perf.get('df') is not None:
            socketio.emit(
                'update_chart',
                {
                    'status'   : 'success',
                    'data'     : perf['df'],           # list[dict] of candles/indicators
                    'precision': float(perf['precision']),
                    'minMove'  : float(perf['min_move']),
                    'orders'   : perf['orders'] or [],
                },
                to=str(user_id)
            )
        # --------------------------------------------------------------

        return jsonify({
            'status'     : 'success',
            'performance': perf,
            'logs'       : logs,
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching bot stats: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500
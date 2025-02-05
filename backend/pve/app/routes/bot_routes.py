from flask import Blueprint, request, jsonify, current_app
from ..utils.token_utils import token_required
from ..models.bot_model import Bot
import redis

bot_bp = Blueprint('bot_bp', __name__)
redis_client = redis.Redis(host='localhost', port=6379, db=0)

@bot_bp.route('/api/bots', methods=['GET'])
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
def create_bot():
    """
    Create a new bot (but do not launch it yet).
    """
    try:
        request_data = request.get_json()
        user_id = request_data.get('user_id')
        name = request_data.get('name')
        parameters = request_data.get('parameters')

        if not user_id or not name or not parameters:
            return jsonify({'error': 'Missing required parameters'}), 400

        bot_id = Bot.create(user_id, name, parameters)
        return jsonify({'status': 'success', 'message': 'Bot created', 'bot_id': bot_id}), 201
    except Exception as e:
        current_app.logger.error(f"Error creating bot: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bot_bp.route('/api/bots/<int:bot_id>/start', methods=['POST'])
def start_bot(bot_id):
    """
    Start a bot.
    """
    try:
        Bot.update_status(bot_id, 'to_be_launched')

        redis_client.publish('bot-launch-channel', str(bot_id))

        return jsonify({'status': 'success', 'message': f'Bot {bot_id} is launching...'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bot_bp.route('/api/bots/<int:bot_id>/stop', methods=['POST'])
def stop_bot(bot_id):
    """
    Stop a bot via Redis.
    """
    try:
        Bot.update_status(bot_id, 'to_be_stopped')

        redis_client.publish('bot-stop-channel', str(bot_id))

        return jsonify({'status': 'success', 'message': f'Bot {bot_id} is stopping...'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bot_bp.route('/api/bots/<int:bot_id>/performance', methods=['GET'])
@token_required
def bot_performance(bot_id):
    """
    Get bot performance metrics.
    """
    try:
        performance = 1  # Placeholder for actual performance data
        return jsonify({'status': 'success', 'performance': performance})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

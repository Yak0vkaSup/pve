# app/routes/auth_routes.py
from flask import Blueprint, request, jsonify, current_app
from ..utils.token_utils import save_user_token, verify_user_token, is_dev_mode
from ..utils.logger import log_request
from ..models.user_model import User
from ..models.graph_model import Graph
from .graph_routes import load_template_graph_for_user
import time
import hmac
import hashlib
import binascii
import uuid

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/api/telegram-auth', methods=['POST'])
@log_request
def receive_telegram_auth():
    BOT_TOKEN = current_app.config['TELEGRAM_BOT_TOKEN']
    try:
        user_data = request.get_json()
        user_id = user_data.get('id')
        
        # Check if this is a new user
        is_new_user = not User.user_exists(user_id) if user_id else True
        
        if is_dev_mode():
            # In dev mode, use a more predictable user ID but allow template reloading
            dev_user_id = "123456789"
            user_data['id'] = dev_user_id
            user_data['first_name'] = user_data.get('first_name', 'Dev')
            user_data['last_name'] = user_data.get('last_name', 'User')
            user_data['username'] = user_data.get('username', 'DevUser')
            
            user_token = str(uuid.uuid4())
            save_user_token(user_data, user_token)
            
            # Check if dev user has any graphs, if not, load templates
            existing_graphs = Graph.get_all_by_user(dev_user_id)
            if not existing_graphs:
                current_app.logger.info(f"Loading template graphs for dev user {dev_user_id}")
                template_loaded = load_template_graph_for_user(dev_user_id)
                if template_loaded:
                    current_app.logger.info("Template graphs loaded successfully for dev user")
                else:
                    current_app.logger.warning("No template graphs were loaded for dev user")
            else:
                current_app.logger.info(f"Dev user already has {len(existing_graphs)} graphs")
            
            return jsonify({
                'status': 'success', 
                'message': 'Dev mode authorization successful', 
                'token': user_token,
                'dev_mode': True,
                'templates_loaded': not existing_graphs
            })

        # Production mode - original Telegram validation logic
        received_hash = user_data.pop('hash', None)

        if not received_hash:
            return jsonify({'status': 'error', 'message': 'Missing hash parameter'}), 400

        try:
            received_hash_bytes = binascii.unhexlify(received_hash)
        except binascii.Error:
            return jsonify({'status': 'error', 'message': 'Invalid hash format'}), 400

        data_check_arr = [f"{key}={value}" for key, value in sorted(user_data.items()) if value != '']
        data_check_string = '\n'.join(data_check_arr).rstrip('\n')
        secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
        computed_hash_bytes = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).digest()

        if computed_hash_bytes != received_hash_bytes:
            return jsonify({'status': 'error', 'message': 'Invalid hash, data integrity failed'}), 400

        current_time = int(time.time())
        if current_time - int(user_data['auth_date']) > 86400:
            return jsonify({'status': 'error', 'message': 'Auth data is outdated'}), 400

        user_token = str(uuid.uuid4())
        save_user_token(user_data, user_token)
        
        # Load template graph for new users in production
        if is_new_user and user_id:
            current_app.logger.info(f"Loading template graph for new user {user_id}")
            load_template_graph_for_user(user_id)
            
        return jsonify({'status': 'success', 'message': 'Authorization successful', 'token': user_token})
    except Exception as e:
        current_app.logger.error(f"Exception occurred: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@auth_bp.route('/api/load-dev-templates', methods=['POST'])
@log_request
def load_dev_templates():
    """Endpoint to manually load template graphs in dev mode"""
    if not is_dev_mode():
        return jsonify({'status': 'error', 'message': 'Only available in development mode'}), 403
    
    try:
        dev_user_id = "123456789"
        template_loaded = load_template_graph_for_user(dev_user_id)
        
        if template_loaded:
            graphs = Graph.get_all_by_user(dev_user_id)
            return jsonify({
                'status': 'success', 
                'message': f'Template graphs loaded successfully',
                'graph_count': len(graphs)
            })
        else:
            return jsonify({
                'status': 'warning', 
                'message': 'No template graphs found or error loading templates'
            })
    except Exception as e:
        current_app.logger.error(f"Error loading dev templates: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@auth_bp.route('/api/verify-token', methods=['POST'])
@log_request
def verify_token():
    try:
        if is_dev_mode():
            return jsonify({'status': 'success', 'message': 'Token is valid'})
        data = request.get_json()
        user_id = data.get('id')
        user_token = data.get('token')

        if not user_id or not user_token:
            return jsonify({'status': 'error', 'message': 'Missing user ID or token'}), 400

        if verify_user_token(user_id, user_token):
            return jsonify({'status': 'success', 'message': 'Token is valid'})
        else:
            return jsonify({'status': 'error', 'message': 'Invalid token'}), 401
    except Exception as e:
        current_app.logger.error(f"Exception during token verification: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

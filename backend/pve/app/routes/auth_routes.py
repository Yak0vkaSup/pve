# app/routes/auth_routes.py
from flask import Blueprint, request, jsonify, current_app
from ..utils.token_utils import save_user_token, verify_user_token
from ..utils.logger import log_request
from ..models.user_model import User
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
        return jsonify({'status': 'success', 'message': 'Authorization successful', 'token': user_token})
    except Exception as e:
        current_app.logger.error(f"Exception occurred: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

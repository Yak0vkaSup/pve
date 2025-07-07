# app/utils/token_utils.py
from functools import wraps
from flask import request, jsonify, current_app
from .database import get_db_connection
from ..models.bot_model import Bot


def save_user_token(user_data, token):
    user_id = user_data.get('id')
    first_name = user_data.get('first_name')
    last_name = user_data.get('last_name', '')
    username = user_data.get('username', '')

    conn = get_db_connection()
    cursor = conn.cursor()
    # Check if user exists
    query = "SELECT id FROM users WHERE id = %s"
    cursor.execute(query, (user_id,))
    existing_user = cursor.fetchone()

    if existing_user:
        # Update token
        update_query = """
            UPDATE users
            SET usertoken = %s,
                last_auth = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        cursor.execute(update_query, (token, user_id))
    else:
        # Insert new user
        insert_query = """
            INSERT INTO users (id, first_name, last_name, username, usertoken, auth_date)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """
        cursor.execute(insert_query, (user_id, first_name, last_name, username, token))

    conn.commit()
    cursor.close()
    conn.close()

def verify_user_token(user_id, user_token):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT usertoken FROM users WHERE id = %s"
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result:
        return result[0] == user_token
    return False

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_token = None
        if request.method == 'POST':
            data = request.get_json()
            user_token = data.get('token')
            user_id = data.get('id') or data.get('user_id')
        else:
            user_token = request.args.get('token')
            user_id = request.args.get('id') or request.args.get('user_id')

        if not user_token or not user_id:
            return jsonify({'status': 'error', 'message': 'Token or user ID is missing'}), 403

        if not verify_user_token(user_id, user_token):
            return jsonify({'status': 'error', 'message': 'Session expired or invalid token'}), 401
        request.user_id = user_id
        return f(*args, **kwargs)
    return decorated

def bot_owner_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        bot_id  = kwargs.get('bot_id')
        user_id = getattr(request, 'user_id', None)

        if bot_id is None or user_id is None:
            return jsonify({'status': 'error',
                            'message': 'Unauthorized or malformed request'}), 401

        if not Bot.is_owned_by(bot_id, user_id):
            # 404 rather than 403 to avoid leaking valid bot IDs
            return jsonify({'status': 'error', 'message': 'Bot not found'}), 404

        return f(*args, **kwargs)
    return decorated

def is_dev_mode():
    flask_env = current_app.config.get('FLASK_ENV', '').lower()
    return flask_env in ['dev', 'development']

# app/utils/token_utils.py
from functools import wraps
from flask import request, jsonify, current_app
from .database import get_db_connection

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
            SET usertoken = %s
            WHERE id = %s
        """
        cursor.execute(update_query, (token, user_id))
    else:
        # Insert new user
        insert_query = """
            INSERT INTO users (id, first_name, last_name, username, usertoken)
            VALUES (%s, %s, %s, %s, %s)
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
            return jsonify({'status': 'error', 'message': 'Invalid user token or user ID'}), 403

        return f(*args, **kwargs)
    return decorated

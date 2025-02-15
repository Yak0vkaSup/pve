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

from functools import wraps
from flask import request, jsonify, current_app

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

        # Perform token verification (Replace this with your actual verification function)
        if not verify_user_token_logic(token):  # Replace with actual token verification function
            return jsonify({'status': 'error', 'message': 'Invalid or expired token'}), 403

        return f(*args, **kwargs)

    return decorated_function


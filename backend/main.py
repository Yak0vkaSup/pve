from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import time
import hashlib
import hmac
import uuid
import base64
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

graph_json = None

def connect_to_db():
    conn = psycopg2.connect(
        host='localhost',
        database='postgres',
        user='postgres',
        password='postgres'
    )
    return conn

@app.route('/api/telegram-auth', methods=['POST'])
def receive_telegram_auth():
    user = request.get_json()
    print(type(user))
    # Extract user data from the request
    user_id = user.get('id')
    first_name = user.get('first_name', '')
    last_name = user.get('last_name', '')
    username = user.get('username', '')
    auth_date = user.get('auth_date')
    hash_value = user.get('hash')

    # Create the data_check_string by sorting keys alphabetically
    fields = [
        f"auth_date={auth_date}",
        f"first_name={first_name}",
        f"id={user_id}",
        f"username={username}"
    ]
    data_check_string = "\n".join(fields)
    print(f"Data Check String: {data_check_string}")
    BOT_TOKEN = "6180226975:AAHePZ0wipSWogSkZDFXmf6tm8DwDXVPgJI"

    # Generate the secret key by hashing the bot token using SHA-256
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    
    # Generate the HMAC-SHA-256 signature
    hmac_signature = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).digest()

    # Decode the received hash from Base64 to bytes for comparison
    received_hash = base64.b64decode(hash_value)

    # Log both signatures for comparison
    print(f"Generated Signature: {hmac_signature.hex()}")
    print(f"Received Hash: {received_hash.hex()}")
    if hmac_signature != hash_value:
        return jsonify({'status': 'error', 'message': 'Invalid authentication data'}), 400

    current_timestamp = int(time.time())
    if current_timestamp - int(auth_date) > 21600:
        return jsonify({'status': 'error', 'message': 'Authentication data is outdated'}), 400

    user_exist = check_user_exists(user_id)
    user_token = uuid.uuid4()
    print('exist', user_exist)
    if not user_exist:
        print(user_token)
        save_user_to_db(user)

    save_user_token()


    
    # Return a success message
    return jsonify({'status': 'success', 'message': 'Success'})

@app.route('/api/update-user', methods=['POST'])
def update_user():
    data = request.get_json()

    user_id = data.get('id')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    key = data.get('key')
    key_secret = data.get('key_secret')

    if not user_id:
        return jsonify({'status': 'error', 'message': 'User ID is required'}), 400

    conn = connect_to_db()
    cursor = conn.cursor()

    # Update user information in the database
    query = """
    UPDATE users
    SET first_name = %s, last_name = %s, key = %s, key_secret = %s
    WHERE id = %s
    """
    cursor.execute(query, (first_name, last_name, key, key_secret, user_id))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'status': 'success', 'message': 'User data updated successfully'})


@app.route('/api/user-data', methods=['POST'])
def user_data():
    data = request.get_json()
    
    # Extract user data properly
    user = data.get('user')
    
    if user:
        user_exists = check_user_exists(user['id'])  # Check if user exists in the DB
        if user_exists:
            user_info = get_user_from_db(user['id'])
            return jsonify({'status': 'success', 'message': 'User exists', 'user_info': user_info})
        else:
            save_user_to_db(user)
            return jsonify({'status': 'success', 'message': 'User data received and processed'})
    else:
        return jsonify({'status': 'error', 'message': 'User data not found in the request'}), 400

def get_user_from_db(user_id):
    """Retrieve user information from the database"""
    conn = connect_to_db()
    cursor = conn.cursor()

    # Query to fetch user information including key and key_secret
    query = """
    SELECT id, first_name, last_name, username, auth_date, key, key_secret 
    FROM users 
    WHERE id = %s
    """
    cursor.execute(query, (user_id,))
    user_info = cursor.fetchone()

    cursor.close()
    conn.close()

    # Convert the fetched data to a dictionary
    if user_info:
        return {
            'id': user_info[0],
            'first_name': user_info[1],
            'last_name': user_info[2],
            'username': user_info[3],
            'auth_date': user_info[4].isoformat(),  # Convert datetime to string
            'key': user_info[5],
            'key_secret': user_info[6]
        }
    return None

def check_user_exists(user_id):
    """Check if a user with the given ID exists in the database"""
    conn = connect_to_db()
    cursor = conn.cursor()

    query = "SELECT EXISTS(SELECT 1 FROM users WHERE id = %s)"
    cursor.execute(query, (user_id,))
    user_exists = cursor.fetchone()[0]
    cursor.close()
    conn.close()

    return user_exists

def save_user_token(user_id, token):
    """Update the usertoken for an existing user in the database"""

    conn = connect_to_db()
    cursor = conn.cursor()

    # Update query to set the usertoken for the user with the given id
    query = """
    UPDATE users
    SET usertoken = %s
    WHERE id = %s
    """
    cursor.execute(query, (token, user_id))
    conn.commit()

    cursor.close()
    conn.close()


def save_user_to_db(user):
    """Insert a new user into the database"""
    user_id = user['id']
    first_name = user['first_name']
    last_name = user.get('last_name', '')
    username = user.get('username', '')
    auth_date = datetime.utcfromtimestamp(user['auth_date'])
    
    conn = connect_to_db()
    cursor = conn.cursor()

    query = """
    INSERT INTO users (id, first_name, last_name, username, auth_date)
    VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (user_id, first_name, last_name, username, auth_date))
    conn.commit()

    cursor.close()
    conn.close()





def get_date_delta_days_ago(delta):
    date_days_ago = datetime.now() - timedelta(delta)
    return date_days_ago.strftime('%Y-%m-%d')

@app.route('/api/receive-graph', methods=['POST'])
def receive_graph():
    global graph_json
    graph_json = request.get_json()
    print('Received graph JSON:')
    print(graph_json)
    # Notify all connected clients that the graph has been updated
    socketio.emit('graph_updated', {'message': 'Graph has been updated'})
    return jsonify({'status': 'success', 'message': 'Graph received'})

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('fetch_data')
def handle_fetch_data(data):

    global graph_json
    # Extract symbol from graph_json
    if not graph_json:
        emit('update_chart', {'status': 'error', 'message': 'Graph JSON not received yet'})
        return

    nodes = graph_json.get("nodes", [])
    symbol = None

    # Iterate over nodes to find the symbol
    for node in nodes:
        if node.get("type") == "custom/fetch":
            properties = node.get("properties", {})
            symbol = properties.get("symbol")
            if symbol:
                break  # Symbol found, exit the loop

    if symbol is None:
        emit('update_chart', {'status': 'error', 'message': 'Symbol not found in graph JSON'})
        return

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=15)
    limit = data.get('limit', 100000)  # Default limit to 100000 rows
    offset = data.get('offset', 0)  # Default offset to 0 (start from the beginning)

    conn = connect_to_db()
    query = f"""
    SELECT timestamp AS date, open, high, low, close, volume
    FROM candles
    WHERE symbol = '{symbol}' AND
          timestamp BETWEEN '{start_date}' AND '{end_date}'
    ORDER BY timestamp
    LIMIT {limit} OFFSET {offset};
    """
    df = pd.read_sql(query, conn)
    conn.close()

    # Convert the timestamp to a Unix timestamp in seconds
    df['date'] = pd.to_datetime(df['date'], utc=True)
    df['date'] = df['date'].astype(int) // 10**9  # Convert to Unix timestamp in seconds

    result = df.to_dict(orient="records")
    # Emit the data back to the client
    emit('update_chart', {'status': 'success', 'data': result})

    
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)

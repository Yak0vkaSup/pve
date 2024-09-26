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
import binascii
import uuid
import json

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
    BOT_TOKEN = "6180226975:AAHePZ0wipSWogSkZDFXmf6tm8DwDXVPgJI"
    try:
        # Parse incoming JSON
        user_data = request.get_json()
        received_hash = user_data.pop('hash', None)

        if not received_hash:
            return jsonify({'status': 'error', 'message': 'Missing hash parameter'}), 400

        # Convert received hash from hex to binary format (bytes)
        try:
            received_hash_bytes = binascii.unhexlify(received_hash)
        except binascii.Error as e:
            print("Error converting received hash to bytes:", e)
            return jsonify({'status': 'error', 'message': 'Invalid hash format'}), 400

        data_check_arr = [f"{key}={value}" for key, value in sorted(user_data.items()) if value != '']
        data_check_string = '\n'.join(data_check_arr).rstrip('\n')
        secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
        computed_hash_bytes = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).digest()

        if computed_hash_bytes != received_hash_bytes:
            print(f"Hash mismatch!\nReceived hash (bytes): {received_hash_bytes}\nComputed hash (bytes): {computed_hash_bytes}")
            return jsonify({'status': 'error', 'message': 'Invalid hash, data integrity failed'}), 400

        # Optional: Check if auth_date is not too old (e.g., within the last 24 hours)
        current_time = int(time.time())
        if current_time - int(user_data['auth_date']) > 86400:  # 86400 seconds = 24 hours
            print("Auth data is outdated.")
            return jsonify({'status': 'error', 'message': 'Auth data is outdated'}), 400

        user_token = str(uuid.uuid4())
        save_user_token(user_data, user_token)
        print("Authorization successful! User token generated:", user_token)

        # Return a success message<
        return jsonify({
            'status': 'success',
            'message': 'Authorization successful',
            'token': user_token  # Return the generated token
        })
    except Exception as e:
        # Debug: Print the error message
        print("Exception occurred:", str(e))
        return jsonify({'status': 'error', 'message': str(e)}), 400


def save_user_token(user_data, token):
    """Update the usertoken for an existing user in the database"""
    user_id = user_data.get('id')
    first_name = user_data.get('first_name')
    last_name = user_data.get('last_name', '') 
    username = user_data.get('username', '')  
    photo_url = user_data.get('photo_url', '') 


    # Get all existing user IDs from the database
    existing_ids = get_all_user_ids()

    conn = connect_to_db()
    cursor = conn.cursor()
    
    if user_id in existing_ids:
        print('User exists, updating token.')
        # If the user ID exists, update the token
        update_query = """
        UPDATE users
        SET usertoken = %s
        WHERE id = %s
        """
        cursor.execute(update_query, (token, user_id))
    else:
        print('New user, inserting user data and token.')
        # If the user ID doesn't exist, insert a new record with all user details
        insert_query = """
        INSERT INTO users (id, first_name, last_name, username, photo_url, usertoken) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (user_id, first_name, last_name, username, photo_url, token))

    conn.commit()
    cursor.close()
    conn.close()

def get_all_user_ids():
    """Retrieve all user ids from the database."""
    conn = connect_to_db()
    cursor = conn.cursor()

    query = "SELECT id FROM users"

    cursor.execute(query)
    existing_ids = cursor.fetchall()

    # Convert the result into a flat list of user ids
    existing_ids = [row[0] for row in existing_ids]

    cursor.close()
    conn.close()
    return existing_ids

@app.route('/api/get-user-info', methods=['POST'])
def get_user_info():
    try:
        # Get data from the request
        request_data = request.get_json()
        user_id = request_data.get('id')
        user_token = request_data.get('token')

        # Check if user_id or token is missing
        if not user_id or not user_token:
            return jsonify({'status': 'error', 'message': 'Missing user ID or token'}), 400

        # Verify the user's token
        if not verify_user_token(user_id, user_token):
            return jsonify({'status': 'error', 'message': 'Invalid user token or user ID'}), 403

        # If the token is valid, retrieve user info
        conn = connect_to_db()
        cursor = conn.cursor()

        query = """
        SELECT first_name, last_name, username, key, key_secret 
        FROM users 
        WHERE id = %s
        """
        cursor.execute(query, (user_id,))
        user_data = cursor.fetchone()

        conn.close()

        if not user_data:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        # Respond with user data
        user_info = {
            'first_name': user_data[0],
            'last_name': user_data[1],
            'username': user_data[2],
            'key': user_data[3],
            'key_secret': user_data[4]
        }

        return jsonify({'status': 'success', 'user_info': user_info})
    except Exception as e:
        print(f"Error fetching user info: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/update-user', methods=['POST'])
def update_user():
    try:
        # Get the request data
        request_data = request.get_json()

        # Extract the user_id and user_token from the request data
        user_id = request_data.get('id')
        user_token = request_data.get('token')

        # Extract the updated user data
        first_name = request_data.get('first_name')
        last_name = request_data.get('last_name')
        key = request_data.get('key')
        key_secret = request_data.get('key_secret')

        # Check if all required fields are provided
        if not user_id or not user_token:
            return jsonify({'status': 'error', 'message': 'Missing user ID or token'}), 400

        # Verify the user token
        if not verify_user_token(user_id, user_token):
            return jsonify({'status': 'error', 'message': 'Invalid user token or user ID'}), 403

        # Connect to the database and update the user's information
        conn = connect_to_db()
        cursor = conn.cursor()

        # Update query
        update_query = """
        UPDATE users
        SET first_name = %s, last_name = %s, key = %s, key_secret = %s
        WHERE id = %s
        """
        cursor.execute(update_query, (first_name, last_name, key, key_secret, user_id))
        conn.commit()

        cursor.close()
        conn.close()

        # Respond with success
        return jsonify({'status': 'success', 'message': 'User data updated successfully'})
    
    except Exception as e:
        print(f"Error updating user data: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

    
def verify_user_token(user_id, user_token):
    """Verify if the provided token matches the token stored in the database."""
    try:
        # Connect to the database
        conn = connect_to_db()
        cursor = conn.cursor()

        # Query to get the usertoken by user_id
        query = """
        SELECT usertoken 
        FROM users 
        WHERE id = %s
        """
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        # If no result, the user ID does not exist
        if result is None:
            return False

        # Fetch the token from the result
        stored_token = result[0]
        print(stored_token)
        # Compare the provided token with the stored token
        return stored_token == user_token
    except Exception as e:
        print(f"Error verifying user token: {str(e)}")
        return False

# Route to save or update the graph in the database
@app.route('/api/save-graph', methods=['POST'])
def save_graph():
    try:
        request_data = request.get_json()

        # Extract the user ID, graph name, and serialized graph data from the request
        user_id = request_data.get('user_id')
        graph_name = request_data.get('name')
        graph_data = request_data.get('graph_data')
        user_token = request_data.get('token')

        if not user_id or not graph_name or not graph_data:
            return jsonify({'status': 'error', 'message': 'Missing user ID, graph name, or graph data'}), 400

        # Verify the user token
        if not verify_user_token(user_id, user_token):
            return jsonify({'status': 'error', 'message': 'Invalid user token'}), 403

        conn = connect_to_db()
        cursor = conn.cursor()

        # Check if the user already has a graph with the same name
        query = "SELECT id FROM user_graphs WHERE user_id = %s AND name = %s"
        cursor.execute(query, (user_id, graph_name))
        existing_graph = cursor.fetchone()

        if existing_graph:
            # Update the existing graph
            update_query = """
            UPDATE user_graphs
            SET graph_data = %s, created_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND name = %s
            """
            cursor.execute(update_query, (json.dumps(graph_data), user_id, graph_name))
        else:
            # Insert new graph
            insert_query = """
            INSERT INTO user_graphs (user_id, name, graph_data, created_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            """
            cursor.execute(insert_query, (user_id, graph_name, json.dumps(graph_data)))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success', 'message': 'Graph saved successfully'})
    except Exception as e:
        print(f"Error saving graph: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/get-saved-graphs', methods=['GET'])
def get_saved_graphs():
    user_id = request.args.get('user_id')
    user_token = request.args.get('token')

    # Verify user token
    if not verify_user_token(user_id, user_token):
        return jsonify({'status': 'error', 'message': 'Invalid user token'}), 403

    # Check if the user ID is provided
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Missing user ID'}), 400

    conn = connect_to_db()
    cursor = conn.cursor()

    query = "SELECT id, name FROM user_graphs WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    graphs = cursor.fetchall()

    cursor.close()
    conn.close()

    graph_list = [{'id': graph[0], 'name': graph[1]} for graph in graphs]
    return jsonify({'status': 'success', 'graphs': graph_list})

@app.route('/api/load-graph', methods=['POST'])
def load_graph():
    try:
        request_data = request.get_json()

        # Extract the user ID, graph name, and user token from the request
        user_id = request_data.get('user_id')
        graph_name = request_data.get('name')
        user_token = request_data.get('token')

        if not user_id or not graph_name:
            return jsonify({'status': 'error', 'message': 'Missing user ID or graph name'}), 400

        # Verify the user token
        if not verify_user_token(user_id, user_token):
            return jsonify({'status': 'error', 'message': 'Invalid user token'}), 403

        conn = connect_to_db()
        cursor = conn.cursor()

        # Query to get the graph data for the given user and graph name
        query = "SELECT graph_data FROM user_graphs WHERE user_id = %s AND name = %s"
        cursor.execute(query, (user_id, graph_name))
        graph = cursor.fetchone()

        cursor.close()
        conn.close()

        # If no graph is found, return an error
        if not graph:
            return jsonify({'status': 'error', 'message': 'Graph not found'}), 404

        # Return the graph data
        return jsonify({'status': 'success', 'graph_data': graph[0]})
    
    except Exception as e:
        print(f"Error loading graph: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

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
    print(nodes)
    # PARSING
    ''' ici a la place d'iteration faut rajouter une fonction'''
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

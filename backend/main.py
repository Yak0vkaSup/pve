from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

graph_json = None
secret_key = '2bc4d44e9ee1c83cd764e54658bc5db3c2ef9223943d88e8c30035b0471466ece5b2bab3c1095e905444851f84f2672e72f650a5035e1dad363bfaf026ea745a'

def connect_to_db():
    conn = psycopg2.connect(
        host='localhost',
        database='postgres',
        user='postgres',
        password='postgres'
    )
    return conn

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
    print(data)


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

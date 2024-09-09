from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
import psycopg2
import pandas as pd
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

def connect_to_db():
    conn = psycopg2.connect(
        host='localhost',
        database='postgres',
        user='postgres',
        password='postgres'
    )
    return conn

@app.route('/api/fetch-data', methods=['POST'])
def fetch_data():
    data = request.json
    symbol = data.get('symbol')
    start_date = data.get('start_date')
    end_date = datetime.utcnow()
    limit = data.get('limit', 100000)  # Default limit to 1000 rows
    offset = data.get('offset', 0)  # Default offset to 0 (start from the beginning)

    conn = connect_to_db()
    query = f"""
    SELECT timestamp AS date, open, high, low, close, volume
    FROM candles
    WHERE symbol = '{symbol}' AND
          timestamp BETWEEN '{start_date}' AND '{end_date}'
    ORDER BY timestamp
    LIMIT {limit} OFFSET {offset};  -- Fetch data with limit and offset
    """
    df = pd.read_sql(query, conn)
    conn.close()

    # Convert the timestamp to a Unix timestamp in seconds
    df['date'] = pd.to_datetime(df['date'], utc=True)
    df['date'] = df['date'].astype(int) // 10**9  # Convert to Unix timestamp in seconds
    
    result = df.to_dict(orient="records")

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)

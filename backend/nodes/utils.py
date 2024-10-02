import time
import pandas as pd
from pybit.unified_trading import HTTP
from pybit.unified_trading import WebSocket
import pandas_ta as ta
import psycopg2
import os
import logging
from datetime import datetime, timedelta
import json

def calculate_ma(df, length, ma_type, calculate_on, ma_multiplier=1.0):
    ma_function = getattr(ta, ma_type)
    return ma_function(df[calculate_on], length, talib=True) * ma_multiplier

def connect_to_db():
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='postgres',
            user='postgres',
            password='postgres'
        )
        logging.info("Connected to database successfully")
        return conn
    except Exception as e:
        logging.error(f"Error connecting to database: {e}")
        return None

def fetch_data(symbol, start_date, end_date):
    conn = connect_to_db()
    if conn is None:
        return None
    query = f"""
    SELECT timestamp AS date, open, high, low, close, volume
    FROM candles
    WHERE symbol = '{symbol}' AND
          timestamp BETWEEN '{start_date}' AND '{end_date}'
    ORDER BY timestamp;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    logging.info(f"Fetched data for {symbol} from {start_date} to {end_date}")
    # Ensure the 'date' column is timezone-aware
    df['date'] = pd.to_datetime(df['date'], utc=True)
    return df
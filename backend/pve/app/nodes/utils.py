# app/nodes/utils.py
import pandas as pd
import pandas_ta as ta
from ..utils.database import get_db_connection
import logging

def calculate_ma(df, length, ma_type, calculate_on, ma_multiplier=1.0):
    ma_function = getattr(ta, ma_type)
    return ma_function(df[calculate_on], length, talib=True) * ma_multiplier

def fetch_data(symbol, start_date, end_date):
    conn = get_db_connection()
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
    df['date'] = pd.to_datetime(df['date'], utc=True)
    return df

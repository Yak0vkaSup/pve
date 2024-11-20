import logging
from datetime import datetime, timedelta
import pandas as pd
import psycopg2
from pybit.unified_trading import HTTP
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

def connect_to_db():
    conn = psycopg2.connect(
        host='192.168.1.153',
        database='postgres',
        user='postgres',
        password='postgres'
    )
    return conn

def fetch_data(symbol, start_date, end_date):
    conn = connect_to_db()
    query = f"""
       SELECT timestamp AS date, open, high, low, close, volume
       FROM candles
       WHERE symbol = '{symbol}' AND
             timestamp BETWEEN '{start_date}' AND '{end_date}'
       ORDER BY timestamp;
       """
    df = pd.read_sql(query, conn)
    conn.close()
    df['date'] = pd.to_datetime(df['date'], utc=True)
    df.set_index('date', inplace=True)
    return df

if __name__ == '__main__':
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=180)
    df = fetch_data('BTCUSDT', start_date, end_date)

    # Convert the index to numeric values for fitting the polynomial
    x = np.arange(len(df))  # numeric representation of dates
    y = df['close'].values  # close prices

    # Polynomial fit of degree 5
    poly = np.polyfit(x, y, deg=5)
    poly_fit = np.polyval(poly, x)

    # Plotting the close prices and polynomial fit using Plotly
    fig = go.Figure()

    # Original close price line
    fig.add_trace(go.Scatter(x=df.index, y=y, mode='lines', name='BTCUSDT Close Prices'))

    # Polynomial fit line
    fig.add_trace(go.Scatter(x=df.index, y=poly_fit, mode='lines', name='Polynomial Fit', line=dict(color='blue')))
    channel = 0.03
    fig.add_trace(go.Scatter(x=df.index, y=poly_fit+poly_fit*channel, mode='lines', name='Polynomial high', line=dict(color='green')))
    fig.add_trace(go.Scatter(x=df.index, y=poly_fit-poly_fit*channel, mode='lines', name='Polynomial low', line=dict(color='red')))

    # Update layout
    fig.update_layout(title='BTCUSDT Close Prices with Polynomial Fit', xaxis_title='Date', yaxis_title='Price')
    fig.show()
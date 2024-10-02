import logging
from datetime import datetime, timedelta
import pandas as pd
import psycopg2
from pybit.unified_trading import HTTP
from datetime import datetime, timedelta
session = HTTP(testnet=False)
import plotly.express as px
import numpy as np

def connect_to_db():
    conn = psycopg2.connect(
        host='localhost',
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
    start_date = end_date - timedelta(days=15)
    df = fetch_data('BTCUSDT', start_date, end_date)
     # Plotting 'close' column from the dataframe using Plotly
    fig = px.line(df, x=df.index, y='close', title='BTCUSDT Close Prices')
    fig.show()

    # Creating sine wave with noise and polynomial fit
    x = np.linspace(0, 1, 1000)
    f = 1/4
    sine = np.sin(2 * np.pi * f * x) + np.random.normal(scale=0.1, size=len(x))

    # Polynomial fit of degree 5
    poly = np.polyfit(x, sine, deg=5)

    # Plotting the sine wave and polynomial fit using Matplotlib
    fig, ax = plt.subplots()
    ax.plot(x, sine, label='Data (Sine + Noise)')
    ax.plot(x, np.polyval(poly, x), label='Polynomial Fit', color='red')
    ax.legend()
    ax.set_title('Sine Wave with Polynomial Fit')
    plt.show()
# utils.py
import pandas as pd
import logging
from datetime import datetime, timedelta, timezone
from bybit_api import Bybit

logger = logging.getLogger(__name__)

def prepare_data(symbol, days, timeframe):
    """
    Fetch data for the past `days` days. This is just an example
    reusing your logic.
    """
    bybit_anon = Bybit(api_key="", api_secret="", testnet=False)  # or separate session
    start_date = pd.Timestamp.now(tz=timezone.utc) - timedelta(days=days)
    end_date = pd.Timestamp.now(tz=timezone.utc) - timedelta(minutes=1)
    df = get_candles(bybit_anon, symbol, timeframe, start_date, end_date)
    return df
def get_candles(bybit_instance, symbol, timeframe, start_date, end_date):
    logging.debug(f"Fetching candles for {symbol} from {start_date} to {end_date}")
    candles_data = []
    limit_bars = 1000
    while start_date < end_date:
        candles = bybit_instance.session.get_kline(symbol=symbol, interval=timeframe, start=int(start_date.timestamp() * 1000),
                                    limit=limit_bars)
        candles_list = candles['result']['list']
        start_date = pd.to_datetime(int(candles_list[0][0]), unit='ms', utc=True)
        candles_data += candles_list[::-1]  # .extend(candles_list.reverse())
        if len(candles_list) < limit_bars:
            break

    df = pd.DataFrame(candles_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)

    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['open'] = pd.to_numeric(df['open'], errors='coerce')
    df['high'] = pd.to_numeric(df['high'], errors='coerce')
    df['low'] = pd.to_numeric(df['low'], errors='coerce')
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

    df = df.drop_duplicates(subset='timestamp', keep='first')
    print(f"Candles fetched and processed successfully for symbol - {symbol}")
    return df


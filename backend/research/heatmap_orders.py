import time
import dash
from dash import dcc, html
from dash.dependencies import Output, Input
import plotly.graph_objs as go
from pybit.unified_trading import WebSocket as BybitWebSocket, HTTP
from threading import Thread
import pandas as pd
from collections import deque
from plotly.subplots import make_subplots
import pandas_ta as ta

#########################################
# 1. FETCH INSTRUMENT INFO FOR BASE TICK SIZE
#########################################
def get_price_interval(symbol, category="linear"):
    """
    Fetch the instrument info for a given symbol and return the tickSize as float.
    """
    session = HTTP(testnet=False)
    response = session.get_instruments_info(category=category, symbol=symbol)
    if response.get("retCode") == 0:
        result_list = response.get("result", {}).get("list", [])
        if result_list:
            tick_size = float(result_list[0]["priceFilter"]["tickSize"])
            print(f"Base tickSize for {symbol}: {tick_size}")
            return tick_size
    print("Failed to fetch tickSize; defaulting to 0.003")
    return 0.003  # fallback

# For our symbol, fetch the base tick size.
symbol = "BTCUSDT"
category = "linear"
base_tick_size = get_price_interval(symbol, category)

#########################################
# 2. DYNAMIC PRICE INTERVAL FUNCTION
#########################################
def get_dynamic_price_interval(tick_size, mid_price, percentage=0.0002):
    """
    Calculate a dynamic price interval (bin width) as the larger of:
      - The instrument’s tick_size (the minimum possible price step)
      - A fixed percentage of the mid_price

    For example, for BTC with mid_price ≈ 20000:
      mid_price * percentage = 20000 * 0.0002 = 4,
    so the dynamic interval will be max(tick_size, 4). For BTC, if tick_size is 0.1,
    then the interval becomes 4.

    For a low-priced symbol like TONUSDT (price around 5), if tick_size is 0.003,
    then 5 * 0.0002 = 0.001, so the function returns 0.003.
    """
    dynamic_interval = max(tick_size, mid_price * percentage)
    print(f"Mid price: {mid_price:.2f} -> dynamic price interval: {dynamic_interval:.6f}")
    return dynamic_interval


#########################################
# 3. DASH APP SETUP
#########################################
app = dash.Dash(__name__)
app.layout = html.Div([
    dcc.Graph(id='live-orderbook-chart', style={'height': '100vh'}),
    dcc.Interval(id='interval-component', interval=1 * 1000, n_intervals=0)
])

#########################################
# 4. DATA STORAGE (DEQUES)
#########################################
max_length = 5000000
orderbook_data = {
    'time': deque(maxlen=max_length),
    'bids': deque(maxlen=max_length),
    'asks': deque(maxlen=max_length)
}
ticker_data_bybit = {
    'time': deque(maxlen=max_length),
    'lastPrice': deque(maxlen=max_length)
}
trade_data = {
    'time': deque(maxlen=max_length),
    'price': deque(maxlen=max_length),
    'size': deque(maxlen=max_length),
    'side': deque(maxlen=max_length)
}
liquidation_data = {
    'time': deque(maxlen=max_length),
    'price': deque(maxlen=max_length),
    'size': deque(maxlen=max_length),
    'side': deque(maxlen=max_length)
}

# Global DataFrames for aggregated orderbook data
aggregated_bids_df = pd.DataFrame(columns=['time', 'price', 'size'])
aggregated_asks_df = pd.DataFrame(columns=['time', 'price', 'size'])
lowest_bid_prices = pd.DataFrame(columns=['time', 'price'])
lowest_ask_prices = pd.DataFrame(columns=['time', 'price'])
size_difference_data = pd.DataFrame(columns=['time', 'size_difference'])

#########################################
# 5. SET UP BYBIT WEBSOCKET (REAL DATA)
#########################################
ws_bybit = BybitWebSocket(
    testnet=False,          # Using live data
    channel_type="linear",  # USDT Perpetual
)

###########################
# Bybit WebSocket Handlers
###########################
def handle_orderbook_message_bybit(message):
    global orderbook_data
    try:
        data = message['data']
        timestamp = pd.to_datetime(message['ts'], unit='ms')
        bids = [[float(bid[0]), float(bid[1])] for bid in data['b']]
        asks = [[float(ask[0]), float(ask[1])] for ask in data['a']]
        orderbook_data['time'].append(timestamp)
        orderbook_data['bids'].append(bids)
        orderbook_data['asks'].append(asks)
    except Exception as e:
        print(f"Error processing orderbook message from Bybit: {e}")

def handle_ticker_message_bybit(message):
    global ticker_data_bybit
    try:
        data = message['data']
        timestamp = pd.to_datetime(message['ts'], unit='ms')
        last_price = float(data['lastPrice'])
        ticker_data_bybit['time'].append(timestamp)
        ticker_data_bybit['lastPrice'].append(last_price)
    except Exception as e:
        print(f"Error processing ticker message from Bybit: {e}")

def handle_trade_message(message):
    global trade_data
    try:
        trades = message.get('data', [])
        for data in trades:
            timestamp = pd.to_datetime(data['T'], unit='ms')
            price = float(data['p'])
            size = float(data['v'])
            side = data['S']
            trade_data['time'].append(timestamp)
            trade_data['price'].append(price)
            trade_data['size'].append(size)
            trade_data['side'].append(side)
    except Exception as e:
        print(f"Error processing trade message: {e}")

def handle_liquidation_message(message):
    global liquidation_data
    try:
        data = message['data']
        timestamp = pd.to_datetime(data['updateTime'], unit='ms')
        price = float(data['price'])
        size = float(data['size'])
        side = data['side']
        liquidation_data['time'].append(timestamp)
        liquidation_data['price'].append(price)
        liquidation_data['size'].append(size)
        liquidation_data['side'].append(side)
    except Exception as e:
        print(f"Error processing liquidation message: {e}")

#####################################
# Subscribe to Bybit WebSocket Streams
#####################################
def subscribe_streams():
    ws_bybit.orderbook_stream(depth=500, symbol=symbol, callback=handle_orderbook_message_bybit)
    ws_bybit.ticker_stream(symbol=symbol, callback=handle_ticker_message_bybit)
    ws_bybit.trade_stream(symbol=symbol, callback=handle_trade_message)
    ws_bybit.liquidation_stream(symbol=symbol, callback=handle_liquidation_message)

thread = Thread(target=subscribe_streams)
thread.daemon = True
thread.start()

##############################################
# 6. DATA AGGREGATION FUNCTIONS FOR THE HEATMAP
##############################################
def aggregate_orderbook_data(df, price_interval):
    def aggregate_side(side):
        side_df = pd.DataFrame(side, columns=['price', 'size'])
        # Group each price to the nearest lower multiple of price_interval
        side_df['price_group'] = (side_df['price'] // price_interval) * price_interval
        aggregated_side = side_df.groupby('price_group').agg({'size': 'sum'}).reset_index()
        return aggregated_side

    aggregated_bids = []
    aggregated_asks = []

    for index in range(len(df)):
        bids = aggregate_side(df['bids'].iloc[index])
        asks = aggregate_side(df['asks'].iloc[index])
        time_ = df['time'].iloc[index]

        for _, bid in bids.iterrows():
            aggregated_bids.append([time_, bid['price_group'], bid['size']])
        for _, ask in asks.iterrows():
            aggregated_asks.append([time_, ask['price_group'], ask['size']])

    aggregated_bids_df_ = pd.DataFrame(aggregated_bids, columns=['time', 'price', 'size'])
    aggregated_asks_df_ = pd.DataFrame(aggregated_asks, columns=['time', 'price', 'size'])
    return aggregated_bids_df_, aggregated_asks_df_

# Global variable to store the dynamic interval once calculated.
DYNAMIC_INTERVAL = None

# Define a window size (for example, the last 1000 entries)
WINDOW_SIZE = 1000

def get_aligned_data(data_dict):
    """
    Takes a dictionary whose values are deques and returns a new dictionary
    where each key has only the last N entries, where N is the minimum length
    across all keys.
    """
    # Convert deques to lists
    lists = {k: list(v) for k, v in data_dict.items()}
    # Find the minimum length
    min_len = min(len(lst) for lst in lists.values())
    # Use only the last min_len items, and then optionally take the last WINDOW_SIZE items
    aligned = {k: lst[-min_len:][-WINDOW_SIZE:] for k, lst in lists.items()}
    return aligned

def prepare_data():
    global orderbook_data, ticker_data_bybit, trade_data, liquidation_data, \
           aggregated_bids_df, aggregated_asks_df, lowest_bid_prices, lowest_ask_prices, \
           size_difference_data, DYNAMIC_INTERVAL

    # Use aligned copies of the deques to avoid mismatched lengths.
    aligned_orderbook = get_aligned_data(orderbook_data)
    orderbook_df = pd.DataFrame(aligned_orderbook)

    aligned_ticker = get_aligned_data(ticker_data_bybit)
    ticker_df_bybit = pd.DataFrame(aligned_ticker)

    aligned_trade = get_aligned_data(trade_data)
    trade_df = pd.DataFrame(aligned_trade)

    aligned_liquidation = get_aligned_data(liquidation_data)
    liquidation_df = pd.DataFrame(aligned_liquidation)

    if not orderbook_df.empty:
        # Convert timestamps to seconds since epoch.
        orderbook_df['time'] = orderbook_df['time'].astype('int64') // 10 ** 9

        # Compute the dynamic interval only once.
        if DYNAMIC_INTERVAL is None:
            latest_bids = orderbook_df['bids'].iloc[-1]
            latest_asks = orderbook_df['asks'].iloc[-1]
            if latest_bids and latest_asks:
                best_bid = max([bid[0] for bid in latest_bids])
                best_ask = min([ask[0] for ask in latest_asks])
                mid_price = 0.5 * (best_bid + best_ask)
                DYNAMIC_INTERVAL = get_dynamic_price_interval(base_tick_size, mid_price)
            else:
                DYNAMIC_INTERVAL = base_tick_size  # fallback

        # Use the locked dynamic interval for aggregation.
        new_bids_df, new_asks_df = aggregate_orderbook_data(orderbook_df.iloc[-1:], price_interval=DYNAMIC_INTERVAL / 10)

        aggregated_bids_df = pd.concat([aggregated_bids_df, new_bids_df]).reset_index(drop=True)
        aggregated_asks_df = pd.concat([aggregated_asks_df, new_asks_df]).reset_index(drop=True)

        # (Rest of your aggregation code remains the same)
        latest_bids = orderbook_df['bids'].iloc[-1]
        latest_asks = orderbook_df['asks'].iloc[-1]
        lowest_bid_price = max([bid[0] for bid in latest_bids]) if latest_bids else None
        lowest_ask_price = min([ask[0] for ask in latest_asks]) if latest_asks else None
        time_ = orderbook_df['time'].iloc[-1]

        if lowest_bid_price is not None:
            lowest_bid_prices = pd.concat([
                lowest_bid_prices,
                pd.DataFrame({'time': [time_], 'price': [lowest_bid_price]})
            ]).reset_index(drop=True)
        if lowest_ask_price is not None:
            lowest_ask_prices = pd.concat([
                lowest_ask_prices,
                pd.DataFrame({'time': [time_], 'price': [lowest_ask_price]})
            ]).reset_index(drop=True)

        last_bids_50 = aggregated_bids_df.tail(50) if not aggregated_bids_df.empty else None
        last_asks_50 = aggregated_asks_df.tail(50) if not aggregated_asks_df.empty else None
        if last_bids_50 is not None and last_asks_50 is not None:
            total_bids_size = last_bids_50['size'].sum()
            total_asks_size = last_asks_50['size'].sum()
            size_diff = total_asks_size - total_bids_size
            size_difference_data = pd.concat([
                size_difference_data,
                pd.DataFrame({'time': [time_], 'size_difference': [size_diff]})
            ]).reset_index(drop=True)
            if len(size_difference_data) > 1:
                size_difference_data['EMA'] = ta.ema(size_difference_data['size_difference'], length=40)
                ema_min = size_difference_data['EMA'].min()
                ema_max = size_difference_data['EMA'].max()
                if ema_max != ema_min:
                    size_difference_data['Scaled_EMA'] = 6.4 + (size_difference_data['EMA'] - ema_min) * (6.6 - 6.4) / (ema_max - ema_min)

    if not ticker_df_bybit.empty:
        ticker_df_bybit['time'] = ticker_df_bybit['time'].astype('int64') // 10 ** 9
    if not trade_df.empty:
        trade_df['time'] = trade_df['time'].astype('int64') // 10 ** 9
    if not liquidation_df.empty:
        liquidation_df['time'] = liquidation_df['time'].astype('int64') // 10 ** 9

    return orderbook_df, ticker_df_bybit, trade_df, liquidation_df

########################################
# 7. DASH CALLBACK: UPDATE THE CHART
########################################
@app.callback(
    Output('live-orderbook-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_chart(n):
    global aggregated_bids_df, aggregated_asks_df, lowest_bid_prices, lowest_ask_prices, size_difference_data
    orderbook_df, ticker_df_bybit, trade_df, liquidation_df = prepare_data()

    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.9, 0.1],
        specs=[[{"type": "xy"}, {"type": "xy"}]]
    )

    # HEATMAP: BIDS (GREEN) & ASKS (RED)
    if not aggregated_bids_df.empty:
        fig.add_trace(go.Heatmap(
            x=aggregated_bids_df['time'],
            y=aggregated_bids_df['price'],
            z=aggregated_bids_df['size'],
            colorscale='Greens',
            name='Bids',
            showscale=False
        ), row=1, col=1)
    if not aggregated_asks_df.empty:
        fig.add_trace(go.Heatmap(
            x=aggregated_asks_df['time'],
            y=aggregated_asks_df['price'],
            z=aggregated_asks_df['size'],
            colorscale='Reds',
            name='Asks',
            showscale=False
        ), row=1, col=1)

    # TRADES: BUY = green, SELL = red
    if not trade_df.empty:
        buy_trades = trade_df[trade_df['side'] == 'Buy']
        sell_trades = trade_df[trade_df['side'] == 'Sell']
        fig.add_trace(go.Scatter(
            x=buy_trades['time'],
            y=buy_trades['price'],
            mode='markers',
            name='Buy Trades',
            marker=dict(
                size=[size * 0.01 for size in buy_trades['size']],
                color='green', opacity=0.6, symbol='circle'
            )
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=sell_trades['time'],
            y=sell_trades['price'],
            mode='markers',
            name='Sell Trades',
            marker=dict(
                size=[size * 0.01 for size in sell_trades['size']],
                color='red', opacity=0.6, symbol='circle'
            )
        ), row=1, col=1)

    # TICKER: LAST PRICE (Bybit)
    if not ticker_df_bybit.empty:
        fig.add_trace(go.Scatter(
            x=ticker_df_bybit['time'],
            y=ticker_df_bybit['lastPrice'],
            mode='lines',
            name='Bybit Last Price',
            line=dict(color='blue', width=2)
        ), row=1, col=1)

    # LOWEST BIDS & ASKS (DOTTED LINES)
    if not lowest_bid_prices.empty:
        fig.add_trace(go.Scatter(
            x=lowest_bid_prices['time'],
            y=lowest_bid_prices['price'],
            mode='lines',
            name='Lowest Bids',
            line=dict(color='green', width=2, dash='dot')
        ), row=1, col=1)
    if not lowest_ask_prices.empty:
        fig.add_trace(go.Scatter(
            x=lowest_ask_prices['time'],
            y=lowest_ask_prices['price'],
            mode='lines',
            name='Lowest Asks',
            line=dict(color='red', width=2, dash='dot')
        ), row=1, col=1)

    # LIQUIDATIONS
    if not liquidation_df.empty:
        buy_liquidations = liquidation_df[liquidation_df['side'] == 'Buy']
        sell_liquidations = liquidation_df[liquidation_df['side'] == 'Sell']
        fig.add_trace(go.Scatter(
            x=buy_liquidations['time'],
            y=buy_liquidations['price'],
            mode='markers',
            name='Buy Liquidations',
            marker=dict(size=[sz * 100 for sz in buy_liquidations['size']], color='blue', opacity=0.5)
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=sell_liquidations['time'],
            y=sell_liquidations['price'],
            mode='markers',
            name='Sell Liquidations',
            marker=dict(size=[sz * 100 for sz in sell_liquidations['size']], color='purple', opacity=0.5)
        ), row=1, col=1)

    # BAR CHART FOR LAST 50 BIDS/ASKS (RIGHT)
    tail = 50
    last_bids = aggregated_bids_df.tail(tail) if not aggregated_bids_df.empty else None
    last_asks = aggregated_asks_df.tail(tail) if not aggregated_asks_df.empty else None
    if last_bids is not None and not last_bids.empty:
        fig.add_trace(go.Bar(
            x=last_bids['size'],
            y=last_bids['price'],
            name='Bids',
            orientation='h',
            marker=dict(color='green')
        ), row=1, col=2)
    if last_asks is not None and not last_asks.empty:
        fig.add_trace(go.Bar(
            x=last_asks['size'],
            y=last_asks['price'],
            name='Asks',
            orientation='h',
            marker=dict(color='red')
        ), row=1, col=2)

    fig.update_layout(
        title='Live Bybit Order Book Depth (500-Level) with Last Prices & Trades',
        showlegend=True,
        legend=dict(x=0.01, y=0.99, orientation="h"),
        template='plotly_dark',
        uirevision='constant-value'
    )
    fig.update_yaxes(title_text="Price", row=1, col=2)
    fig.update_xaxes(title_text="Size", row=1, col=2)
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)

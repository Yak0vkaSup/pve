from pybit.unified_trading import WebSocket
from time import sleep
ws = WebSocket(
    testnet=False,
    channel_type="linear",
)
def handle_message(message):
    print(message)
ws.kline_stream(
    interval=5,
    symbol="BTCUSDT",
    callback=handle_message
)
while True:
    sleep(1)
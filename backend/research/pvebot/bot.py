import threading
import time
import logging
from enum import Enum
from typing import Dict, Any
from datetime import timedelta

from numpy.distutils.command.config import config

from nodes_bot import process_graph
from bybit_api import Bybit
from dca import DCA
from utils_bot import prepare_data, get_data, fetch_data, timeframes, seconds_since_midnight, get_db_connection
import pandas as pd
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

class BotStatus(Enum):
    STOPPED = 0
    RUNNING = 1
    ERROR = 2

class Bot:
    def __init__(self, bot_id: int, config: dict):
        """
        :param bot_id: Unique ID for this bot (e.g., "SOLUSDT_Bot").
        :param config: Trading config: symbol, timeframe, DCA settings, etc.
        """
        self.bot_id = bot_id
        self.config = config
        self.nodes = None
        self.settings = None
        self.thread = None
        self.stop_signal = False
        self.status = BotStatus.STOPPED
        self.bybit = Bybit(api_key=config['api_key'], api_secret=config['api_secret'], testnet=False)

    def to_dict(self) -> Dict[str, Any]:
        """
        Return a dict representation of the bot for JSON storage.
        """
        return {
            "bot_id": self.bot_id,
            "config": self.config,
            "status": self.status.name,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """
        Recreate a Bot instance from a dict (loaded from JSON).
        """
        bot_id = data["bot_id"]
        config = data["config"]
        status = data["status"]
        bot = cls(bot_id=bot_id, config=config)
        bot.status = BotStatus[status]
        return bot

    def start(self):
        """
        Start a thread (or direct call) that runs the DCA strategy in a loop.
        """
        if self.status == BotStatus.RUNNING:
            logger.info(f"Bot '{self.bot_id}' is already running.")
            return

        self.stop_signal = False
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        self.status = BotStatus.RUNNING

    def stop(self):
        """
        Signal the thread to stop and wait for it to join.
        """
        if self.status != BotStatus.RUNNING:
            logger.info(f"Bot '{self.bot_id}' is not running.")
            return

        self.stop_signal = True
        if self.thread:
            self.thread.join(timeout=10)
        self.status = BotStatus.STOPPED
        logger.info(f"Bot '{self.bot_id}' stopped.")

    def run(self):
        """
        Outline:
        1. Initialize variables
        2. Loop:
           - Fetch new data
           - Process signals
           - If no DCA position is open and signal is True => open DCA
           - If DCA position is open => check PnL, time, close if needed
        """

        logger.info(f"Bot '{self.bot_id}' is running with config: {self.config}")
        self.status = BotStatus.RUNNING

        symbol = self.config['symbol']
        timeframe = self.config['timeframe']

        # Keep track of whether we have an active DCA trade
        dca_active = False
        dca = None
        # Time when we opened the current trade
        trade_start_time = time.time() #None

        while not self.stop_signal:
            try:
                # -----------------------------
                # 1) Fetch the most recent data
                # -----------------------------
                if self.config['data_source'] == 0:
                    # Live data from API
                    df = prepare_data(symbol=symbol, days=1, timeframe=timeframe)
                else:
                    # or fetch from DB / other source
                    start_date = pd.Timestamp.now(tz=timezone.utc) - timedelta(days=1)
                    end_date = pd.Timestamp.now(tz=timezone.utc)
                    df = fetch_data(symbol, start_date, end_date)
                    # or: df = get_data(1, symbol, timeframe)

                # -----------------------------
                # 2) Process signals
                # -----------------------------
                if not dca_active:
                    nodes = self.config['nodes']
                    df, settings = process_graph(nodes, df, symbol)
                    self.settings = settings
                    signals_series = settings['signals']

                    # last_alert = signals_series.iloc[-2] if you want the last *closed* candle
                    last_alert = signals_series.iloc[-2] if len(signals_series) >= 2 else False

                # -----------------------------
                # 3) If there's a new signal AND we do NOT have a trade open => Open DCA
                # -----------------------------
                dca_active = True
                if  not dca_active: #last_alert and
                    initial_price = float(df.iloc[-1]['close'])
                    logger.info(f"Detected new buy signal. Initializing DCA at price {initial_price}")

                    try:
                        dca = DCA(
                            initial_price=initial_price,
                            order_size_usdt=settings['first_order_size_usdt'],
                            step_percentage=settings['step_percentage'],
                            num_orders=settings['num_orders'],
                            martingale_factor=settings['martingale_factor'],
                            bybit_instance=self.bybit,
                            symbol=symbol,
                        )
                        dca.calculate_orders()
                        dca.place_long_orders()

                        # Update our local state to track this is an active DCA
                        dca_active = True
                        trade_start_time = time.time()

                    except Exception as e:
                        logger.error(f"Failed to initialize DCA for bot '{self.bot_id}': {e}")
                        self.status = BotStatus.ERROR
                        # Depending on your preference, you might break or continue.
                        continue

                # -----------------------------
                # 4) If a DCA trade is currently open, monitor it
                # -----------------------------
                if dca_active:
                    try:
                        # Get current position info
                        long_pos, short_pos = self.bybit.get_positions(symbol)
                        current_long_pnl = long_pos.pnl
                        current_long_pnl_perc = long_pos.pnl_perc

                        logger.info(
                            f"[{self.bot_id}] In position => PnL: {current_long_pnl:.4f}, "
                            f"PnL%: {current_long_pnl_perc:.2f}%"
                        )

                        # 4a) Check profit target
                        if current_long_pnl_perc >= self.settings['profit_target']:
                            logger.info(
                                f"[{self.bot_id}] Profit target ({self.settings['profit_target']}%) reached. Exiting..."
                            )
                            self._exit_position(long_pos.qty)
                            dca_active = False
                            dca = None
                            continue

                        # 4b) Check time-based stop
                        elapsed = time.time() - trade_start_time
                        if elapsed > self.config.get('max_trade_duration', 3600):
                            logger.info(
                                f"[{self.bot_id}] Max trade duration reached. Closing position..."
                            )
                            self._exit_position(long_pos.qty)
                            dca_active = False
                            dca = None
                            continue

                        self.save_performance()

                        time.sleep(5)

                    except Exception as e:
                        logger.error(f"[{self.bot_id}] Error checking open position: {e}")
                        self.status = BotStatus.ERROR
                        continue
                else:
                    timeframe_seconds = timeframes[self.config['timeframe']]
                    while True:
                        current_second = seconds_since_midnight()

                        # Check if we've hit a multiple of the timeframe in seconds
                        if current_second % timeframe_seconds == 0:
                            break
                        time.sleep(1)

            except Exception as e:
                logger.error(f"[{self.bot_id}] Error in main loop: {e}")
                self.status = BotStatus.ERROR
                break

        logger.info(f"Bot '{self.bot_id}' main loop ended.")

    def _exit_position(self, qty):
        """
        Helper to exit a long position and cancel orders.
        """
        if qty > 0:
            self.bybit.exit(side="Sell", qty=qty, index=1, SYMBOL=self.config['symbol'])
        self.bybit.cancel_all_orders(self.config['symbol'])
        self.stop()

    def save_performance(self):
        """
        Fetches and stores the latest bot performance stats in the database.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch current position info
        long_pos, _ = self.bybit.get_positions(self.config['symbol'])

        # Fetch historical PnL and trade history
        pnl_history = self.bybit.get_pnl_history(self.config['symbol'])
        trades = self.bybit.get_trade_history(self.config['symbol'])

        last_pnl = pnl_history[0]['closedPnl'] if pnl_history else 0
        total_trades = len(trades)

        query = """
            INSERT INTO bot_performance (bot_id, profit, equity, trades_executed, pnl, drawdown)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query,
                       (self.bot_id, last_pnl, long_pos.positionValue, total_trades, last_pnl, long_pos.pnl_perc))

        conn.commit()
        cursor.close()
        conn.close()

    def update_status(self, status):
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "UPDATE bots SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        cursor.execute(query, (status, self.bot_id))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def get_performance_history(bot_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT timestamp, profit, equity, trades_executed, pnl, drawdown FROM bot_performance WHERE bot_id = %s ORDER BY timestamp DESC"
        cursor.execute(query, (bot_id,))
        performance = cursor.fetchall()
        cursor.close()
        conn.close()
        return performance
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
from utils_bot import prepare_data, get_data, fetch_data
import pandas as pd
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

class BotStatus(Enum):
    STOPPED = 0
    RUNNING = 1
    ERROR = 2

class Bot:
    def __init__(self, bot_id: str, config: dict):
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
        # Create Bybit session from config (you can store keys in config, or from env)
        self.bybit = Bybit(api_key=config['api_key'], api_secret=config['api_secret'])

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
        Main bot loop that places orders, checks positions, etc.
        This example is a simplified approach.
        """
        logger.info(f"Bot '{self.bot_id}' is running with config: {self.config}")

        if self.config['data_source'] == 0:
            # get from API
            df = prepare_data(
                symbol=self.config['symbol'],
                days=1,
                timeframe=self.config['timeframe']
            )
        else:
            start_date = pd.Timestamp.now(tz=timezone.utc) - timedelta(days=1)
            end_date = pd.Timestamp.now(tz=timezone.utc)
            df = fetch_data(self.config['symbol'], start_date, end_date)
            # get from DB
            #df = get_data(1, self.config['symbol'], self.config['timeframe'])
        nodes = self.config['nodes']
        df, settings = process_graph(nodes, df, self.config['symbol'])

        self.settings = settings

        # dca
        initial_price = float(df.iloc[-1]['close'])
        try:
            print(settings)
            print(self.config['symbol'])
            dca = DCA(
                initial_price=initial_price,
                order_size_usdt=settings['first_order_size_usdt'],
                step_percentage=settings['step_percentage'],
                num_orders=settings['num_orders'],
                martingale_factor=settings['martingale_factor'],
                bybit_instance=self.bybit,
                symbol=self.config['symbol'],
            )
            dca.calculate_orders()

            dca.place_long_orders()

        except Exception as e:
            logger.error(f"Failed to initialize DCA for bot '{self.bot_id}': {e}")
            self.status = BotStatus.ERROR
            return

        start_time = time.time()

        while not self.stop_signal:

            time.sleep(5)

            # Check positions
            try:
                long_pos, short_pos = self.bybit.get_positions(self.config['symbol'])
                current_long_pnl = long_pos.pnl
                current_long_pnl_perc = long_pos.pnl_perc

                logger.info(
                    f"[{self.bot_id}] Monitoring => PnL: {current_long_pnl:.4f}, PnL%: {current_long_pnl_perc:.2f}%"
                )

                # Check profit target
                if current_long_pnl_perc >= self.settings['profit_target']:
                    logger.info(
                        f"[{self.bot_id}] Profit target of {self.settings['profit_target']}% reached. Exiting..."
                    )
                    if long_pos.qty > 0:
                        self.bybit.exit(side="Sell", qty=long_pos.qty, index=1, SYMBOL=self.config['symbol'])
                    self.bybit.cancel_all_orders(self.config['symbol'])
                    self.stop()
                    break

                # Time-based stop
                elapsed = time.time() - start_time
                if elapsed > self.config.get('max_trade_duration', 3600):
                    logger.info(
                        f"[{self.bot_id}] Max trade duration reached. Closing position..."
                    )
                    if long_pos.qty > 0:
                        self.bybit.exit(side="Sell", qty=long_pos.qty, index=1, SYMBOL=self.config['symbol'])
                    self.bybit.cancel_all_orders(self.config['symbol'])
                    self.stop()
                    break

            except Exception as e:
                logger.error(f"[{self.bot_id}] Error in main loop: {e}")
                self.status = BotStatus.ERROR
                break

        logger.info(f"Bot '{self.bot_id}' main loop ended.")

import logging
import sys
import json
import multiprocessing
import time
import os
from pve.app.pvebot.bot_manager import BotManager
from pve.app.pvebot.utils_bot import get_db_connection

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/trading_bots.log")
        ]
    )

def run_bot_manager():
    """
    Runs the BotManager in a separate process.
    """
    setup_logging()
    manager = BotManager()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Exiting..")

def main():
    setup_logging()

    # Start BotManager as a separate process
    bot_manager_process = multiprocessing.Process(target=run_bot_manager, daemon=True)
    bot_manager_process.start()

    try:
        bot_manager_process.join()  # Keep process alive
    except KeyboardInterrupt:
        logging.info("Shutting down BotManager...")
        bot_manager_process.terminate()

if __name__ == "__main__":
    """
    Example configuration for testing:
    
    with open("strategy.json", "r") as f:
        data = json.load(f)

    # Data source: 0 = Bybit API, 1 = Local DB
    config = {
        'data_source': 1,
        'api_key': os.environ.get('BYBIT_API_KEY'),        # Set in environment
        'api_secret': os.environ.get('BYBIT_API_SECRET'),  # Set in environment
        'symbol': data['symbol'],
        'timeframe': data['timeframe'],
        'vpl': data,
    }
    """

    main()

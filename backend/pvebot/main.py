import logging
import sys
import json
import multiprocessing
from bot_manager import BotManager
from utils_bot import get_db_connection

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("trading_bots.log")
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
            pass  # Keeps BotManager running indefinitely
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
    with open("boll.json", "r") as f:
        data = json.load(f)

    # datasource 0 is api bybit
    # 1 is DB local
    config = {
        'data_source': 1,
        'api_key': "CQ16qbTLFEbJqLtS4W",
        'api_secret': "E0p4bPZpsgew4STE8kttc6LGhfoXuaRLxgdA",
        'symbol': data['symbol'],
        'timeframe': data['timeframe'],
        'nodes': data,
    }
    """
    main()

import json
import logging
import os
from typing import Dict, Optional
from bot import Bot, BotStatus

logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self, storage_path="bot_states.json"):
        """
        :param storage_path: Path to the JSON file that stores bot states.
        """
        self.storage_path = storage_path
        self.bots: Dict[str, Bot] = {}  # {bot_id: Bot instance}

    def load_bots_from_storage(self):
        """
        Load bot states from a JSON file and recreate Bot instances.
        """
        if not os.path.exists(self.storage_path):
            logger.info("No saved bots to load.")
            return

        try:
            with open(self.storage_path, "r") as f:
                saved_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load bot states: {e}")
            return

        for bot_id, bot_state in saved_data.items():
            # Recreate a Bot instance from saved config/state
            bot = Bot.from_dict(bot_state)
            self.bots[bot_id] = bot
            logger.info(f"Loaded bot '{bot_id}' from storage.")

    def save_bots_to_storage(self):
        """
        Persist all current bots to a JSON file.
        """
        data = {}
        for bot_id, bot in self.bots.items():
            data[bot_id] = bot.to_dict()

        try:
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=4)
            logger.info("Bot states saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save bot states: {e}")

    def create_bot(self, bot_id: str, config: dict):
        """
        Create a new bot with given ID and config. The config
        should contain all strategy parameters, API credentials, etc.
        """
        if bot_id in self.bots:
            logger.warning(f"Bot with ID '{bot_id}' already exists.")
            return self.bots[bot_id]

        bot = Bot(bot_id=bot_id, config=config)
        self.bots[bot_id] = bot
        logger.info(f"Created bot '{bot_id}' with config: {config}")
        self.save_bots_to_storage()
        return bot

    def start_bot(self, bot_id: str):
        """
        Start (launch) a bot’s trading strategy if it’s not already running.
        """
        bot = self.bots.get(bot_id)
        if not bot:
            logger.error(f"No bot found with ID: {bot_id}")
            return

        if bot.status == BotStatus.RUNNING:
            logger.info(f"Bot '{bot_id}' is already running.")
            return

        bot.start()
        logger.info(f"Bot '{bot_id}' has been started.")
        self.save_bots_to_storage()

    def stop_bot(self, bot_id: str):
        """
        Stop a bot’s strategy.
        """
        bot = self.bots.get(bot_id)
        if not bot:
            logger.error(f"No bot found with ID: {bot_id}")
            return

        if bot.status == BotStatus.STOPPED:
            logger.info(f"Bot '{bot_id}' is already stopped.")
            return

        bot.stop()
        logger.info(f"Bot '{bot_id}' has been stopped.")
        self.save_bots_to_storage()

    def remove_bot(self, bot_id: str):
        """
        Completely remove a bot from the manager and storage.
        """
        bot = self.bots.pop(bot_id, None)
        if bot:
            bot.stop()
            logger.info(f"Bot '{bot_id}' removed.")
        self.save_bots_to_storage()

    def get_bot_status(self, bot_id: str) -> Optional[str]:
        bot = self.bots.get(bot_id)
        if not bot:
            return None
        return bot.status.name

    def start_all(self):
        """
        Start all bots that are not running.
        """
        for bot_id in self.bots:
            self.start_bot(bot_id)

    def stop_all(self):
        """
        Stop all bots that are running.
        """
        for bot_id in self.bots:
            self.stop_bot(bot_id)

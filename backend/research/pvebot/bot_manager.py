import logging
import json
import redis
import threading
from typing import Dict, Optional
from utils_bot import get_db_connection
from bot import Bot, BotStatus

logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self):
        """
        Initializes the BotManager and listens for bot launch & stop requests.
        """
        self.bots: Dict[int, Bot] = {}  # {bot_id: Bot instance}
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.load_bots_from_db()

        # Start Redis Pub/Sub listeners
        self.listen_for_bot_events()

    def listen_for_bot_events(self):
        """
        Listens for bot launch & stop requests via Redis Pub/Sub.
        """
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe('bot-launch-channel', 'bot-stop-channel')

        def process_messages():
            for message in pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel'].decode('utf-8')
                    bot_id = int(message['data'].decode('utf-8'))

                    if channel == 'bot-launch-channel':
                        logger.info(f"Received launch request for Bot ID: {bot_id}")
                        self.start_bot(bot_id)
                    elif channel == 'bot-stop-channel':
                        logger.info(f"Received stop request for Bot ID: {bot_id}")
                        self.stop_bot(bot_id)

        thread = threading.Thread(target=process_messages, daemon=True)
        thread.start()

    def load_bots_from_db(self):
        """
        Loads all running bots from MySQL and restores them in memory.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT id, user_id, name, parameters FROM bots WHERE status = 'running'"
        cursor.execute(query)
        rows = cursor.fetchall()

        for row in rows:
            bot_id, user_id, name, parameters = row
            #config = json.loads(parameters)
            bot = Bot(bot_id=bot_id, config=parameters)
            self.bots[bot_id] = bot
            bot.start()

        cursor.close()
        conn.close()
        logger.info(f"Loaded {len(self.bots)} running bots from the database.")

    def start_bot(self, bot_id: int):
        """
        Starts a bot.
        """
        if bot_id in self.bots:
            bot = self.bots[bot_id]
            if bot.status == BotStatus.RUNNING:
                logger.info(f"Bot '{bot_id}' is already running.")
                return
            bot.start()
            logger.info(f"Bot '{bot_id}' has been started.")
        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "SELECT id, user_id, name, parameters FROM bots WHERE id = %s"
            cursor.execute(query, (bot_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if not row:
                logger.error(f"No bot found with ID: {bot_id}")
                return

            _, user_id, name, parameters = row
            #parameters = json.loads(parameters)

            bot = Bot(bot_id=bot_id, config=parameters)
            self.bots[bot_id] = bot
            bot.start()

            # Update status in MySQL
            Bot.update_status(bot_id, 'running')

            logger.info(f"Bot '{bot_id}' (User {user_id}) has been launched.")

    def stop_bot(self, bot_id: int):
        """
        Stops a bot.
        """
        bot = self.bots.get(bot_id)
        if not bot:
            logger.error(f"No bot found with ID: {bot_id}")
            return

        if bot.status == BotStatus.STOPPED:
            logger.info(f"Bot '{bot_id}' is already stopped.")
            return

        bot.stop()
        Bot.update_status(bot_id, 'stopped')

        del self.bots[bot_id]
        logger.info(f"Bot '{bot_id}' has been stopped.")

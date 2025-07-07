# pve/app/pvebot/bot_manager.py
import json
import logging
import os
import threading
from typing import Dict

import redis

from pve.app.pvebot.bot import Bot, BotStatus
from pve.app.pvebot.utils_bot import get_db_connection

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────
# generic logging setup (file + no double handlers)
# ───────────────────────────────────────────────────────────────
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
if not any(isinstance(h, logging.FileHandler) and
           h.baseFilename.endswith("bot_manager.log")
           for h in logger.handlers):
    fh = logging.FileHandler(os.path.join(log_dir, "bot_manager.log"),
                             encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(fh)

logger.setLevel(logging.DEBUG)
logger.propagate = False
# ───────────────────────────────────────────────────────────────


class BotManager:
    """
    Keeps a registry of live Bot objects, launches/halts them on
    Redis PubSub messages and *authoritatively* reconciles status
    with the `bots` SQL table.
    """

    def __init__(self):
        self.bots: Dict[int, Bot] = {}
        self.redis_client = redis.Redis(host="redis", port=6379, db=0)
        self._load_running_bots_from_db()
        self._listen_for_pubsub_events()

    # ────────────────────────────────────────────────────────────
    # public API
    # ────────────────────────────────────────────────────────────
    def start_bot(self, bot_id: int) -> bool:
        """
        Launch a bot if not already running.  ALWAYS creates
        a watcher-thread so the manager can detect crashes
        and patch the DB row.
        """
        from pve.run import app
        try:
            with app.app_context():
                bot = self.bots.get(bot_id)
                if bot and bot.status == BotStatus.RUNNING:
                    logger.info("Bot %s already running.", bot_id)
                    return True

                if bot is None:
                    # hydrate from DB
                    cfg = self._fetch_config(bot_id)
                    if cfg is None:
                        logger.error("No bot found with ID %s", bot_id)
                        return False

                    # optional fast-fail: verify instrument specs exist
                    from pve.app.vpl.nodes import get_precision_and_min_move_local
                    if get_precision_and_min_move_local(cfg["symbol"]) in [(None, None), None]:
                        logger.error("Instrument specs missing for %s – refusing launch.", cfg["symbol"])
                        Bot.update_status("error", bot_id)
                        return False

                    bot = Bot(bot_id, cfg)
                    self.bots[bot_id] = bot

                # launch + always spawn watcher
                bot.start()
                threading.Thread(target=self._watch_bot,
                                 args=(bot_id,),
                                 daemon=True).start()
                logger.info("Bot %s launched.", bot_id)
                return True

        except Exception as exc:
            logger.exception("Error starting bot %s: %s", bot_id, exc)
            Bot.update_status("error", bot_id)
            return False

    def stop_bot(self, bot_id: int) -> None:
        bot = self.bots.get(bot_id)
        if not bot:
            # The bot isn't running in this manager instance (could have crashed or
            # another worker hosts it). Still, honour the stop-request by patching
            # the DB row so the UI does not sit in a perpetual "to_be_stopped" state.
            logger.warning("Stop-request for unknown bot %s – attempting graceful shutdown anyway.", bot_id)

            # Try to close positions/orders using raw config without creating a full Bot instance
            cfg = self._fetch_config(bot_id)
            if cfg:
                # Start emergency flatten in background (non-blocking)
                threading.Thread(
                    target=self._emergency_flatten_positions, 
                    args=(bot_id, cfg), 
                    daemon=True
                ).start()
                logger.info(f"Started background emergency flatten for bot {bot_id}")

            Bot.update_status("stopped", bot_id)
            return
        bot.stop()
        # Safety-net: patch DB even if Bot.stop() failed to persist status
        try:
            Bot.update_status("stopped", bot_id)
        except Exception as exc:
            logger.exception("Failed to patch status to 'stopped' after stopping bot %s: %s", bot_id, exc)

        # Clean from registry so it can be re-launched later
        self._remove_bot_from_registry(bot_id, "normal stop completed")

    # ────────────────────────────────────────────────────────────
    # internals
    # ────────────────────────────────────────────────────────────
    def _watch_bot(self, bot_id: int) -> None:
        """
        Blocks until the bot's worker thread exits, then
        *persists* the final status and purges it from RAM.
        """
        bot = self.bots[bot_id]
        bot.thread.join()

        final = bot.status
        new_status = "stopped" if final != BotStatus.ERROR else "error"
        Bot.update_status(new_status, bot_id)

        if final == BotStatus.ERROR:
            logger.error("Bot %s crashed – row patched to 'error'.", bot_id)
        else:
            logger.info("Bot %s exited cleanly.", bot_id)

        # allow clean re-launch
        reason = "crashed" if final == BotStatus.ERROR else "exited cleanly"
        self._remove_bot_from_registry(bot_id, reason)

    # -----------------------------------------------------------
    def _listen_for_pubsub_events(self) -> None:
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("bot-launch-channel", "bot-stop-channel")

        def loop():
            for msg in pubsub.listen():
                if msg["type"] != "message":
                    continue
                channel = msg["channel"].decode()
                bot_id = int(msg["data"].decode())
                if channel == "bot-launch-channel":
                    logger.info("Launch-request %s", bot_id)
                    self.start_bot(bot_id)
                elif channel == "bot-stop-channel":
                    logger.info("Stop-request %s", bot_id)
                    self.stop_bot(bot_id)

        threading.Thread(target=loop, daemon=True).start()

    # -----------------------------------------------------------
    def _load_running_bots_from_db(self) -> None:
        """
        On manager start-up, reconcile the SQL table with reality:
          • rows marked 'running'         → start & attach
          • rows marked 'to_be_launched'  → start & attach (was queued while manager down)
          • rows marked 'to_be_stopped'   → patch to 'stopped' so UI reflects final state
        """
        conn = get_db_connection("postgresql")
        cur = conn.cursor()
        cur.execute("SELECT id, status, parameters FROM bots WHERE status IN ('running', 'to_be_launched', 'to_be_stopped')")
        for bot_id, status, params in cur.fetchall():
            if status in ("running", "to_be_launched"):
                cfg = params if isinstance(params, dict) else json.loads(params)
                bot = Bot(bot_id, cfg)
                self.bots[bot_id] = bot
                bot.start()
                threading.Thread(target=self._watch_bot,
                                 args=(bot_id,),
                                 daemon=True).start()
            elif status == "to_be_stopped":
                Bot.update_status("stopped", bot_id)
        cur.close()
        conn.close()
        logger.info("Re-attached %d bots from DB.", len(self.bots))

    @staticmethod
    def _fetch_config(bot_id: int) -> dict | None:
        conn = get_db_connection("postgresql")
        cur = conn.cursor()
        cur.execute("SELECT parameters FROM bots WHERE id=%s", (bot_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return None
        params = row[0]
        return params if isinstance(params, dict) else json.loads(params)

    def _emergency_flatten_positions(self, bot_id: int, config: dict) -> None:
        """Emergency position flattening without creating a full Bot instance."""
        try:
            api_key = config.get('api_key')
            api_secret = config.get('api_secret')
            symbol = config.get('symbol')
            
            if not api_key or not api_secret or not symbol:
                logger.warning(f"Bot {bot_id}: Missing API credentials or symbol for emergency flatten")
                return
                
            from pve.app.pvebot.bybit_api import Bybit
            bybit = Bybit(api_key, api_secret, testnet=False)
            
            logger.info(f"Bot {bot_id}: Emergency flattening positions for {symbol}")
            
            # Cancel all orders
            bybit.cancel_all_orders(symbol)
            
            # Get and close positions
            long_pos, short_pos = bybit.get_positions(symbol)
            
            if long_pos and long_pos.qty:
                bybit.exit(side='Sell', qty=long_pos.qty, index=1, SYMBOL=symbol)
                logger.info(f"Bot {bot_id}: Emergency closed long position {long_pos.qty}")
                
            if short_pos and short_pos.qty:
                bybit.exit(side='Buy', qty=short_pos.qty, index=2, SYMBOL=symbol)
                logger.info(f"Bot {bot_id}: Emergency closed short position {short_pos.qty}")
                
        except Exception as exc:
            logger.exception(f"Error in emergency flatten for bot {bot_id}: {exc}")

    def _remove_bot_from_registry(self, bot_id: int, reason: str):
        """Remove bot from registry with logging."""
        if bot_id in self.bots:
            logger.warning(f"Removing bot {bot_id} from registry: {reason}")
            self.bots.pop(bot_id, None)
        else:
            logger.debug(f"Bot {bot_id} not in registry when trying to remove: {reason}")

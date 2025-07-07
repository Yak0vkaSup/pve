import sys
import threading
import time
import os
import json
import pandas as pd
import logging
from enum import Enum
from datetime import datetime, timedelta, timezone
from pve.app.vpl.nodes import process_graph, resample_df
from pve.app.pvebot.utils_bot import prepare_data, fetch_data, timeframes, seconds_since_midnight, get_db_connection
from pve.run import app
from pve.app.utils.logger import DBLogHandler
from pybit.unified_trading import HTTP

logger = logging.getLogger(__name__)

class BotStatus(Enum):
    STOPPED = 'stopped'
    RUNNING = 'running'
    ERROR   = 'error'

class Bot:
    def __init__(self, bot_id: int, config: dict):
        self.bot_id = bot_id
        self.config = config
        self.thread = None
        self.stop_signal = False
        self.status = BotStatus.STOPPED
        self.last_order_timestamp = None
        log_dir = os.path.join("logs", f"bot_{bot_id}")
        os.makedirs(log_dir, exist_ok=True)
        self._graph_state = None
        self.logger = logging.getLogger(f"bot_{bot_id}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False  # avoid double prints

        fh = logging.FileHandler(os.path.join(log_dir, "bot.log"), encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        self.logger.addHandler(fh)

        # — AND — the DB handler
        dbh = DBLogHandler(self.bot_id)
        dbh.setLevel(logging.INFO)  # or DEBUG/WARN as you like
        dbh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        self.logger.addHandler(dbh)

        # Attach the same DB handler to node-level logger so LIVE node events are captured
        nodes_logger = logging.getLogger("pve.app.vpl.nodes")
        # Avoid duplicate handlers for the same bot
        if not any(isinstance(h, DBLogHandler) and getattr(h, "bot_id", None) == self.bot_id for h in nodes_logger.handlers):
            nodes_logger.addHandler(dbh)

        self.logger.propagate = False
        self.logger.info("Initialized Bot %s", bot_id)

        # Lazy Bybit helper – only when we actually need it
        self._bybit = HTTP(
            api_key=self.config.get('api_key'),
            api_secret=self.config.get('api_secret'),
        )

        # keep DB in sync with local status
        self._update_db_status(BotStatus.STOPPED)

    def start(self):
        if self.status == BotStatus.RUNNING:
            return
        
        # Check if there's still an old thread running (from a previous stop that timed out)
        if self.thread and self.thread.is_alive():
            self.logger.warning("[START] Old thread still running from previous stop - waiting for it to finish...")
            self.thread.join(timeout=10)
            if self.thread.is_alive():
                self.logger.error("[START] Cannot start - old thread still stuck after 10s")
                return

        self.stop_signal = False
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        self.status = BotStatus.RUNNING
        self._update_db_status(self.status)

    def stop(self):
        """Graceful user-initiated stop: exit loop, flatten positions, cancel orders."""
        if self.status != BotStatus.RUNNING:
            self.logger.info("[STOP] Bot %s already stopped (status=%s)", self.bot_id, self.status)
            return

        self.logger.info("[STOP] Requested stop for bot %s", self.bot_id)

        # Tell loop to exit and wait a bit
        self.stop_signal = True
        if self.thread and self.thread != threading.current_thread():
            self.logger.info("[STOP] Waiting for trading thread to exit...")
            self.thread.join(timeout=5)  # Reduced timeout
            if self.thread.is_alive():
                self.logger.warning("[STOP] Trading thread didn't exit within 5s, forcing shutdown")

        # Always try to flatten positions, even if thread is stuck
        self.logger.info("[STOP] Closing positions and cancelling orders")
        
        # Try to flatten positions in background (non-blocking)
        try:
            # Start flatten in background but DON'T wait for it
            threading.Thread(target=self._background_flatten, daemon=True).start()
            self.logger.info("[STOP] Started background position flattening")
        except Exception as exc:
            self.logger.warning("[STOP] Failed to start background flatten: %s", exc)

        # Force status update regardless of any above failures
        self.status = BotStatus.STOPPED
        try:
            self._update_db_status(self.status)
            self.logger.info(f"[STOP] Bot {self.bot_id} status updated to 'stopped' in DB")
        except Exception as exc:
            self.logger.exception("Failed to update bot status to 'stopped' in DB: %s", exc)

        self.logger.info(f"Bot {self.bot_id} stopped")

        # Mark the bot as stopped even if the worker thread is still running
        # The worker will eventually exit when fetch_data/process_graph complete
        return

    def run(self):
        """
        – warm-up on history (back-test)
        – run the last candle once in LIVE
        – keep streaming new candles

        Changes vs. your original code:
        1. After the LIVE kick-off we re-attach that last_bar to the rolling
           buffer so the time-series is continuous.
        2. Before writing indicator values we lazily add any new columns to
           self.df_full so `.loc` never fails.
        """
        with app.app_context():
            if self.stop_signal:
                return

            self.logger.info("Bot %s running", self.bot_id)

            # ─── core config ───────────────────────────────────────────
            symbol      = self.config['symbol']
            timeframe   = self.config['timeframe']
            raw_graph   = self.config['vpl']
            graph_json  = json.dumps(raw_graph.get('graph', raw_graph))
            interval    = timeframes[timeframe]
            api_key     = self.config.get('api_key')
            api_secret  = self.config.get('api_secret')

            try:
                # ─── 1) WARM-UP: determine look-back window ───────────────
                _, _, _, lookback = process_graph(
                    graph_json, None, None, symbol, timeframe,
                    warmup_only=True, state=self._graph_state
                )

                now   = datetime.now(timezone.utc)
                start = now - timedelta(seconds=(lookback - 1) * interval)

                # ── fetch historical candles ----------------------------------
                hist_df = fetch_data(symbol, start, now)

                # Guard against empty history (e.g. new symbol / DB lag)
                if hist_df.empty:
                    self.logger.error("[INIT] No historical data for %s between %s and %s – aborting bot.", symbol, start, now)
                    self.status = BotStatus.ERROR
                    self._update_db_status(self.status)
                    return

                hist_df['date'] = pd.to_datetime(hist_df['date'], utc=True)
                hist_df.set_index('date', inplace=True)
                
                # IMPORTANT: Resample the data to match the bot's timeframe
                # This fixes the issue where warmup data was always 1-minute regardless of timeframe
                if timeframe != "1min":
                    hist_df = resample_df(hist_df, timeframe)
                    
                hist_df.reset_index(inplace=True)

                # full back-test  → captures self._graph_state
                final_df, _, _, _, self._graph_state = process_graph(
                    graph_json, None, None, symbol, timeframe,
                    mode='backtest',
                    api_key=api_key, api_secret=api_secret,
                    warmup_only=False,
                    dataframe=hist_df,
                    incremental=False,
                    state=self._graph_state
                )

                # Validate we have data after back-test
                if final_df.empty:
                    self.logger.error("[INIT] process_graph produced no rows for %s – aborting bot.", symbol)
                    self.status = BotStatus.ERROR
                    self._update_db_status(self.status)
                    return

                # save a rolling copy *with* indicators, we will add to it later
                self.lookback_rows  = lookback + 10
                self.last_timestamp = final_df['date'].iloc[-1]

                # ─── wipe local back-test orders before LIVE ───────────────
                from pve.app.vpl.nodes import Node
                Node.orders.clear()
                Node.order_id_counter = 0
                self.logger.info("Cleared back-test orders, switching immediately to LIVE mode")

                # === run the very last bar once in LIVE ===
                last_bar = final_df.tail(1).copy()

                _, _, _, init_orders, self._graph_state = process_graph(
                    graph_json, None, None, symbol, timeframe,
                    mode='live',
                    api_key=api_key, api_secret=api_secret,
                    warmup_only=False,
                    dataframe=last_bar,
                    incremental=True,
                    state=self._graph_state
                )
                for o in init_orders:
                    self.logger.info("[LIVE INIT] New order: %s", o)

                # re-attach the bar so there is **no gap**
                self.df_full = pd.concat([final_df, last_bar]).reset_index(drop=True)

                # update last_timestamp so we don't double-log init orders
                self.last_timestamp = pd.to_datetime(
                    init_orders[-1]['time_created']) if init_orders else self.last_timestamp

                # ─── 2) STREAMING LOOP ─────────────────────────────────────
                def get_next_boundary_time(current_time, minutes_needed):
                    """Calculate exactly when the next complete timeframe period will be available"""
                    current_minute = current_time.minute
                    next_boundary_minute = ((current_minute // minutes_needed) + 1) * minutes_needed
                    
                    if next_boundary_minute >= 60:
                        # Next boundary is in the next hour
                        next_boundary_time = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1, minutes=next_boundary_minute - 60)
                    else:
                        # Next boundary is in the current hour
                        next_boundary_time = current_time.replace(minute=next_boundary_minute, second=0, microsecond=0)
                    
                    return next_boundary_time

                if timeframe == "1min":
                    next_execution = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
                    self.logger.info(f"Bot will process new 1min candles every minute")
                else:
                    minutes_needed = interval // 60
                    next_execution = get_next_boundary_time(now, minutes_needed)
                    self.logger.info(f"Next {timeframe} period will be ready at: {next_execution}")

                while not self.stop_signal:
                    # Calculate how long to wait for the next execution
                    current_time = datetime.now(timezone.utc)
                    wait_seconds = (next_execution - current_time).total_seconds()
                    
                    if wait_seconds > 1:
                        # Sleep in chunks to check stop_signal regularly
                        sleep_time = min(wait_seconds, 10.0)  # Sleep max 10 seconds at a time
                        self.logger.debug(f"Waiting {wait_seconds:.0f} seconds until {next_execution.strftime('%H:%M:%S')}")
                        time.sleep(sleep_time)
                        continue
                    
                    # Add a small delay to ensure all data is written to database
                    if timeframe == "1min":
                        self.logger.debug("Waiting 2 seconds for 1min data to be fully available...")
                        time.sleep(2)
                    else:
                        self.logger.debug("Waiting 5 seconds for data to be fully available...")
                        time.sleep(5)

                    try:
                        current_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)
                        
                        if timeframe == "1min":
                            # For 1min timeframe, fetch the previous minute
                            period_start = current_time - timedelta(minutes=1)
                            period_end = current_time
                            
                            self.logger.info(f"Fetching 1min candle: {period_start} to {period_end}")
                            fresh = fetch_data(symbol, period_start, period_end)
                            
                            # Next execution is 1 minute later
                            next_execution = current_time + timedelta(minutes=1)
                        else:
                            # For larger timeframes, fetch the just-completed period
                            minutes_needed = interval // 60
                            # We want the candles that FILL the just-completed period
                            # e.g., at 21:42, fetch candles 21:39, 21:40, 21:41 (not 21:39-21:42)
                            period_end = current_time - timedelta(minutes=1)  # Last minute of the period
                            period_start = period_end - timedelta(seconds=interval) + timedelta(minutes=1)  # First minute of the period
                            
                            self.logger.info(f"Fetching completed {timeframe} period: {period_start} to {period_end} (inclusive)")
                            fresh = fetch_data(symbol, period_start, period_end + timedelta(minutes=1))  # Make end exclusive
                            
                            # Check if we got the expected number of candles
                            if fresh.empty:
                                self.logger.warning(f"No data received. Waiting 5 more seconds and retrying...")
                                time.sleep(5)
                                fresh = fetch_data(symbol, period_start, period_end)
                                if not fresh.empty:
                                    self.logger.info(f"Retry successful: got {len(fresh)} candles")
                            elif len(fresh) < minutes_needed:
                                self.logger.warning(f"Expected {minutes_needed} candles, got {len(fresh)}. Waiting 10 more seconds and retrying...")
                                time.sleep(10)
                                fresh = fetch_data(symbol, period_start, period_end)
                                if not fresh.empty:
                                    self.logger.info(f"Retry successful: got {len(fresh)} candles")
                            
                            # Calculate next execution time
                            next_execution = get_next_boundary_time(current_time, minutes_needed)
                        
                        if fresh.empty:
                            self.logger.warning(f"No fresh data available, retrying in 3 seconds...")
                            time.sleep(3)
                            continue

                        fresh['date'] = pd.to_datetime(fresh['date'], utc=True)
                        fresh.set_index('date', inplace=True)

                        self.logger.info(f"Fresh data ({len(fresh)} candles): {fresh}")
                        
                        # Only resample if we have a larger timeframe and multiple candles
                        if timeframe != "1min":
                            if len(fresh) > 1:
                                fresh = resample_df(fresh, timeframe)
                                self.logger.info(f"Resampled fresh data: {fresh}")
                            else:
                                self.logger.warning(f"Expected {interval//60} candles for {timeframe} timeframe, but got only {len(fresh)}. Cannot resample properly.")
                        
                        fresh.reset_index(inplace=True)

                        # append, dedupe, keep order
                        self.df_full = (pd.concat([self.df_full, fresh])
                                        .drop_duplicates(subset='date')
                                        .reset_index(drop=True))

                        self.df_slice = self.df_full.tail(self.lookback_rows + 2)

                        out_df, precision, min_move, orders, self._graph_state = process_graph(
                            graph_json, None, None, symbol, timeframe,
                            mode='live',
                            api_key=api_key, api_secret=api_secret,
                            warmup_only=False,
                            dataframe=self.df_slice,
                            incremental=True,
                            state=self._graph_state
                        )

                        # ── add indicator columns *if first time seen* ─────
                        indi_cols = [c for c in out_df.columns if c not in
                                     ('date', 'open', 'high', 'low', 'close', 'volume')]
                        for col in indi_cols:
                            if col not in self.df_full.columns:
                                self.df_full[col] = None

                        # copy indicator values into the matching rows
                        self.df_full.loc[
                            self.df_full['date'].isin(out_df['date']), indi_cols
                        ] = out_df[indi_cols].values

                        # log fresh orders
                        # for o in orders:
                        #     ts = pd.to_datetime(o['time_created'])
                        #     if ts > self.last_timestamp:
                        #         self.logger.info("[LIVE] New order: %s", o)

                        # Ensure instrument specs are valid (otherwise we will log garbage and downstream API fails)
                        if precision is None or min_move is None:
                            raise ValueError(f"Instrument specs missing for {symbol}: precision={precision} min_move={min_move}")

                        self.update_performance(self.df_full, precision, min_move, orders)

                        # Update bot timestamp to track when it was last active
                        self.update_bot_timestamp()

                        # advance clock  
                        self.last_timestamp = current_time
                        self.logger.info(f"Next {timeframe} execution scheduled for: {next_execution.strftime('%H:%M:%S')}")

                    except Exception as exc:
                        # Fatal runtime error inside loop → emergency shutdown
                        self.emergency_shutdown(exc)
                        break

            except Exception as exc:
                # Anything in setup phase (warm-up, etc.)
                self.emergency_shutdown(exc)
            finally:
                self.logger.info("Bot %s loop ended", self.bot_id)

    @staticmethod
    def update_status(status, bot_id):
        conn = get_db_connection('postgresql')
        cur = conn.cursor()
        cur.execute("UPDATE bots SET status=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s", (status, bot_id))
        conn.commit()
        cur.close()
        conn.close()

    def update_bot_timestamp(self):
        """Update the bot's updated_at timestamp in the database"""
        try:
            conn = get_db_connection('postgresql')
            cur = conn.cursor()
            cur.execute("UPDATE bots SET updated_at=CURRENT_TIMESTAMP WHERE id=%s", (self.bot_id,))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as exc:
            self.logger.warning(f"Failed to update bot timestamp: {exc}")

    def update_performance(self, df, precision, min_move, orders):
        """
        Upsert one row per bot with:
          - last_update: now()
          - orders: JSONB
          - df: JSONB (records with unix‑seconds timestamps)
          - precision, min_move: numerics
        """
        df = df.copy()
        # 1) serialize df → list of dicts → JSON string
        if df['date'].dtype != 'datetime64[ns]':
            df['date'] = pd.to_datetime(df['date'], utc=True, errors='coerce')

        df['date'] = (df['date'].astype('int64') // 10 ** 9).astype('int64')
        # ------------------------------------------------------------------ #

        columns_to_ignore = ['date', 'open', 'high', 'low', 'close', 'volume']
        ma_columns = [c for c in df.columns if c not in columns_to_ignore]
        df[ma_columns] = df[ma_columns].astype(object).where(pd.notna(df[ma_columns]), None)
        records = df.to_dict('records')
        df_json = json.dumps(records)

        orders_json = json.dumps(orders)
        ts = datetime.now(timezone.utc)

        conn = get_db_connection('postgresql')
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO bot_performance
              (bot_id, last_update, orders, df, precision, min_move)
            VALUES (
              %(bot_id)s,
              %(ts)s,
              %(orders)s::jsonb,
              %(df)s::jsonb,
              %(precision)s,
              %(min_move)s
            )
            ON CONFLICT (bot_id) DO UPDATE
              SET last_update = EXCLUDED.last_update,
                  orders      = EXCLUDED.orders,
                  df          = EXCLUDED.df,
                  precision   = EXCLUDED.precision,
                  min_move    = EXCLUDED.min_move;
        """, {
            'bot_id':    self.bot_id,
            'ts':        ts,
            'orders':    orders_json,
            'df':        df_json,        # ← pass the JSON string here
            'precision': precision,
            'min_move':  min_move
        })
        conn.commit()
        cur.close()
        conn.close()

    # ────────────────────────────────────────────────────────────────
    # Emergency shutdown: cancel orders and flatten positions
    # ----------------------------------------------------------------

    def _flatten_and_cancel(self):
        """Cancel all orders and flatten any open position for the bot's symbol."""

        symbol = self.config.get('symbol')

        if not self._bybit:
            self.logger.warning("[FLATTEN] Bybit session unavailable – cannot flatten positions (api_key missing or creation failed)")
            return

        if not symbol:
            self.logger.warning("[FLATTEN] Symbol missing in config – cannot flatten positions")
            return

        self.logger.info("[FLATTEN] Bybit session and symbol OK, proceeding with cancellation")
        
        try:
            self.logger.info("[FLATTEN] Cancelling all orders for %s", symbol)
            self._bybit.cancel_all_orders(category='linear',  symbol=symbol)

            pos_resp = self._bybit.get_positions(category='linear', symbol=symbol)
            pos_list = pos_resp.get("result", {}).get("list", [])
            long_qty = 0.0
            short_qty = 0.0
            for p in pos_list:
                side = p.get("side")  # 'Buy' or 'Sell'
                size = float(p.get("size", 0))
                if side in ("Buy", "Long") and size > 0:
                    long_qty += size
                elif side in ("Sell", "Short") and size > 0:
                    short_qty += size

            self.logger.info("[FLATTEN] Position snapshot – long=%s short=%s", long_qty, short_qty)

            # 3) close – market order, reduce-only
            if long_qty:
                self.logger.info("[FLATTEN] Closing long position …")
                self._bybit.place_order(
                    category='linear',
                    symbol=symbol,
                    side="Sell",
                    orderType="Market",
                    qty=long_qty,
                    reduceOnly=True,
                    timeInForce="IOC",
                )
            if short_qty:
                self.logger.info("[FLATTEN] Closing short position …")
                self._bybit.place_order(
                    category='linear',
                    symbol=symbol,
                    side="Buy",
                    orderType="Market",
                    qty=short_qty,
                    reduceOnly=True,
                    timeInForce="IOC",
                )

        except Exception as exc:
            self.logger.exception("Error while flattening/cancelling during shutdown: %s", exc)

    def emergency_shutdown(self, reason: Exception | str):
        """Log fatal error and shut down bot, cancelling orders and closing positions."""
        self.logger.exception("[EMERGENCY] Bot %s encountered fatal error → %s", self.bot_id, reason)
        self.logger.info("[EMERGENCY] Closing positions and cancelling orders")
        self._flatten_and_cancel()

        # Update internal flags so the thread exits gracefully
        self.stop_signal = True
        self.status = BotStatus.ERROR
        self.logger.info("[EMERGENCY] Stopping bot")
        self._update_db_status(self.status)

    # ────────────────────────────────────────────────────────────
    # helpers
    # ----------------------------------------------------------------

    def _update_db_status(self, status):
        """Persist bot status to database using canonical lowercase strings."""
        try:
            if isinstance(status, BotStatus):
                status_val = status.value
            else:
                status_val = str(status).lower()
            Bot.update_status(status_val, self.bot_id)
        except Exception as exc:
            self.logger.exception("Failed to update bot status in DB: %s", exc)

    def _safe_flatten_and_cancel(self):
        """Safe wrapper for flatten_and_cancel to handle exceptions."""
        try:
            self.logger.info("[SAFE_FLATTEN] Starting flatten and cancel operation")
            self._flatten_and_cancel()
            self.logger.info("[SAFE_FLATTEN] Flatten and cancel completed successfully")
        except Exception as exc:
            self.logger.exception("[SAFE_FLATTEN] Error in _safe_flatten_and_cancel: %s", exc)

    def _background_flatten(self):
        """Background flatten operation to be called from stop method."""
        self.logger.info("[BACKGROUND] Starting background flatten operation")
        self._flatten_and_cancel()
        self.logger.info("[BACKGROUND] Background flatten operation completed")

def setup_logging():
    os.makedirs("logs", exist_ok=True)  # make sure the folder exists first
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/trading_bots.log", encoding="utf-8"),
        ],
    )

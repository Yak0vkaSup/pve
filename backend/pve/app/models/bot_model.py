from ..utils.database import get_db_connection
import json
import logging
from pybit.unified_trading import HTTP

class Bot:
    @staticmethod
    def create(user_id, name, parameters):
        """
        Store the bot row; always save JSON **text** in the `parameters` column.
        """
        if not isinstance(parameters, str):
            parameters = json.dumps(parameters)

        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO bots (user_id, name, parameters, status)
            VALUES (%s, %s, %s, 'created')
            RETURNING id
            """,
            (user_id, name, parameters)
        )
        bot_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return bot_id

    @staticmethod
    def get_all_by_user(user_id):
        """
        Return a flat list of bots with basic metadata extracted
        from the `parameters` JSON column.
        """
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "SELECT id, name, status, parameters FROM bots WHERE user_id = %s",
            (user_id,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        bots = []
        for bot_id, name, status, param_val in rows:
            if isinstance(param_val, str):
                try:
                    p = json.loads(param_val)
                except json.JSONDecodeError:
                    p = {}
            elif isinstance(param_val, (dict, list)):
                p = param_val
            else:
                p = {}

            bots.append({
                'id'       : bot_id,
                'name'     : name,
                'status'   : status,
                'symbol'   : p.get('symbol'),
                'timeframe': p.get('timeframe'),
                'strategy' : p.get('strategy'),
            })
        return bots

    @staticmethod
    def update_status(status, bot_id):
        """
        Updates the bot status in the database.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "UPDATE bots SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        cursor.execute(query, (status, bot_id))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def stop(bot_id):
        """
        Stops a bot and updates the status in the database.
        """
        Bot.update_status('stopped', bot_id)

    @staticmethod
    def get_performance(bot_id: int) -> dict:
        """
        Fetch the single up-to-date performance row for this bot.
        """
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT last_update, orders, df, precision, min_move
              FROM bot_performance
             WHERE bot_id = %s
        """, (bot_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return {}

        last_update, orders_json, df_json, precision, min_move = row
        return {
            'last_update':   last_update.isoformat(),
            'orders':        orders_json,    # already a dict/list
            'df':            df_json,        # list of records
            'precision':     float(precision),
            'min_move':      float(min_move),
        }

    @staticmethod
    def get_logs(bot_id: int, limit: int = 100) -> list:
        """
        Fetch the most recent `limit` log lines for this bot.
        """
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT timestamp, level, message
              FROM bot_logs
             WHERE bot_id = %s
             ORDER BY timestamp DESC
             LIMIT %s
        """, (bot_id, limit))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
          {'timestamp': ts.isoformat(), 'level': lvl, 'message': msg}
          for ts, lvl, msg in rows
        ]

    @staticmethod
    def get_logs_paginated(bot_id: int, limit: int = 50, cursor: str = None) -> dict:
        """
        Fetch paginated logs for a bot with cursor-based pagination.
        Logs are ordered chronologically (oldest first, newest last).
        
        Args:
            bot_id: Bot ID
            limit: Number of logs to fetch
            cursor: Timestamp cursor for pagination (ISO format)
            
        Returns:
            Dict with logs list, next cursor, and metadata
        """
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Base query - order chronologically (oldest first)
            if cursor:
                # Parse cursor timestamp and fetch logs newer than cursor
                cur.execute("""
                    SELECT timestamp, level, message
                      FROM bot_logs
                     WHERE bot_id = %s AND timestamp > %s
                     ORDER BY timestamp ASC
                     LIMIT %s
                """, (bot_id, cursor, limit + 1))  # +1 to check if there are more
            else:
                # Fetch oldest logs first
                cur.execute("""
                    SELECT timestamp, level, message
                      FROM bot_logs
                     WHERE bot_id = %s
                     ORDER BY timestamp ASC
                     LIMIT %s
                """, (bot_id, limit + 1))  # +1 to check if there are more
            
            rows = cur.fetchall()
            
            # Check if there are more records
            has_more = len(rows) > limit
            if has_more:
                rows = rows[:limit]  # Remove the extra record
            
            # Format logs
            logs = [
                {
                    'timestamp': ts.isoformat(), 
                    'level': lvl, 
                    'message': msg
                }
                for ts, lvl, msg in rows
            ]
            
            # Determine next cursor
            next_cursor = None
            if has_more and logs:
                next_cursor = logs[-1]['timestamp']
            
            # Get total count for metadata
            cur.execute("SELECT COUNT(*) FROM bot_logs WHERE bot_id = %s", (bot_id,))
            total_logs = cur.fetchone()[0]
            
            return {
                'status': 'success',
                'data': {
                    'logs': logs,
                    'nextPageCursor': next_cursor,
                    'hasMore': has_more,
                    'totalLogs': total_logs,
                    'currentPage': limit
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error fetching logs: {str(e)}'
            }
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def is_owned_by(bot_id: int, user_id: int) -> bool:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM bots WHERE id = %s AND user_id = %s",
                    (bot_id, user_id))
        owned = cur.fetchone() is not None
        cur.close()
        conn.close()
        return owned

    @staticmethod
    def delete(bot_id: int, user_id: int, allowed_states: tuple[str, ...]) -> bool:
        """
        DELETE … WHERE id = bot_id AND user_id = user_id
                       AND status IN allowed_states
        Returns True if a row was deleted, False otherwise.
        """
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            f"""
            DELETE FROM bots
             WHERE id = %s
               AND user_id = %s
               AND status = ANY(%s)
            """,
            (bot_id, user_id, list(allowed_states))
        )
        deleted = cur.rowcount
        conn.commit(); cur.close(); conn.close()
        return deleted == 1

    @staticmethod
    def get_parameters(bot_id: int) -> dict | None:
        """
        Get bot parameters for a specific bot ID.
        Returns the parameters dict or None if bot not found.
        """
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT parameters FROM bots WHERE id = %s", (bot_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return None
            
        params = row[0]
        return params if isinstance(params, dict) else json.loads(params)

    @staticmethod
    def get_updated_at(bot_id: int) -> str | None:
        """
        Get bot's last updated timestamp.
        Returns the timestamp as ISO string or None if bot not found.
        """
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT updated_at FROM bots WHERE id = %s", (bot_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row or not row[0]:
            return None
            
        return row[0].isoformat()

    @staticmethod
    def get_trading_period(bot_id: int) -> tuple[str | None, str | None]:
        """
        Get bot's trading period (created_at to updated_at).
        Returns (start_timestamp_ms, end_timestamp_ms) or (None, None) if bot not found.
        """
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT created_at, updated_at FROM bots WHERE id = %s", (bot_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return None, None
            
        created_at, updated_at = row
        
        # Convert to milliseconds timestamps
        start_ms = str(int(created_at.timestamp() * 1000)) if created_at else None
        end_ms = str(int(updated_at.timestamp() * 1000)) if updated_at else None
        
        return start_ms, end_ms

    @staticmethod
    def get_pnl_data(bot_id: int, limit: int = 50, cursor: str = None) -> dict:
        """
        Fetch PnL data for a bot using its API credentials and trading period.
        Returns formatted PnL data with summary statistics.
        """
        
        logger = logging.getLogger(__name__)
        
        # Get bot configuration
        config = Bot.get_parameters(bot_id)
        if not config:
            logger.error(f"Bot {bot_id} not found")
            return {'status': 'error', 'message': 'Bot not found'}
            
        # Extract required parameters
        api_key = config.get('api_key')
        api_secret = config.get('api_secret')
        symbol = config.get('symbol')
        
        if not all([api_key, api_secret, symbol]):
            logger.error(f"Bot {bot_id} missing credentials: api_key={bool(api_key)}, api_secret={bool(api_secret)}, symbol={symbol}")
            return {'status': 'error', 'message': 'Missing API credentials or symbol'}
            
        # Get trading period
        start_time, end_time = Bot.get_trading_period(bot_id)
        logger.info(f"Bot {bot_id} trading period: {start_time} → {end_time}")
        
        # Initialize Bybit client
        bybit = HTTP(
            api_key=api_key, 
            api_secret=api_secret, 
            testnet=False, 
            recv_window=20000,
            timeout=10
        )
        
        # Prepare parameters for Bybit API
        pnl_params = {
            'category': 'linear',
            'symbol': symbol,
            'limit': limit
        }
        
        if start_time:
            pnl_params['startTime'] = int(start_time)
        if end_time:
            pnl_params['endTime'] = int(end_time)
        if cursor:
            pnl_params['cursor'] = cursor
            
        logger.info(f"Bybit API params: {pnl_params}")
            
        try:
            response = bybit.get_closed_pnl(**pnl_params)
            logger.info(f"Bybit response retCode: {response.get('retCode')}")
            
            if response.get('retCode') == 0:
                result = response.get('result', {})
                pnl_list = result.get('list', [])
                next_cursor = result.get('nextPageCursor')
                
                logger.info(f"Retrieved {len(pnl_list)} trades for bot {bot_id}")
                
                # Calculate summary statistics
                total_pnl = sum(float(trade.get('closedPnl', 0)) for trade in pnl_list)
                total_trades = len(pnl_list)
                winning_trades = len([t for t in pnl_list if float(t.get('closedPnl', 0)) > 0])
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                
                return {
                    'status': 'success',
                    'data': {
                        'symbol': symbol,
                        'trades': pnl_list,
                        'nextPageCursor': next_cursor,
                        'dataUpTo': end_time,
                        'tradingPeriod': {
                            'startTime': start_time,
                            'endTime': end_time
                        },
                        'summary': {
                            'totalPnl': total_pnl,
                            'totalTrades': total_trades,
                            'winningTrades': winning_trades,
                            'winRate': round(win_rate, 2)
                        }
                    }
                }
            else:
                error_msg = f"Bybit API error: {response.get('retMsg', 'Unknown error')}"
                logger.error(error_msg)
                return {'status': 'error', 'message': error_msg}
                
        except Exception as api_error:
            error_msg = f'API error: {str(api_error)}'
            logger.exception(f"Bot {bot_id} PnL fetch failed: {error_msg}")
            return {'status': 'error', 'message': error_msg}
import datetime

from ..utils.database import get_db_connection
import json

class AnalyzerResult:
    @staticmethod
    def save(user_id, graph_name, symbol, metrics, equity_curve, trades_details, backtest_id=None):
        """
        Save or update analyzer result for a given graph (backtest) record.
        Uses a unique combination of user_id, graph_name, and backtest_id as identifier.
        Returns the analyzer result id.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create a unique graph_name that includes backtest_id to avoid conflicts
        unique_graph_name = f"{graph_name}_bt_{backtest_id}" if backtest_id else graph_name
        
        query = "SELECT id FROM analyzer_results WHERE user_id = %s AND graph_name = %s"
        cursor.execute(query, (user_id, unique_graph_name))
        existing = cursor.fetchone()

        equity_curve_json = json.dumps(equity_curve)
        trades_details_json = json.dumps(trades_details)

        symbol_val = symbol or metrics.get('Symbol')
        initial_capital = metrics.get('Initial Capital')
        final_capital = metrics.get('Final Capital')
        first_date = metrics.get('First Date')
        last_date = metrics.get('Last Date')
        df_duration = metrics.get('DF Duration')
        total_pnl = metrics.get('Total PnL')
        total_fees = metrics.get('Total Fees')
        total_funding_cost = metrics.get('Total Funding Cost')
        num_trades = metrics.get('Number of Trades')
        win_rate = metrics.get('Win Rate (%)')
        sharpe_ratio = metrics.get('Sharpe Ratio')
        max_drawdown = metrics.get('Max Drawdown (%)')
        avg_trade_duration = metrics.get('Average Trade Duration')
        global_return = metrics.get('Global Return (%)')

        if existing:
            update_query = """
                UPDATE analyzer_results
                SET 
                    symbol = %s,
                    initial_capital = %s,
                    final_capital = %s,
                    first_date = %s,
                    last_date = %s,
                    df_duration = %s,
                    total_pnl = %s,
                    total_fees = %s,
                    total_funding_cost = %s,
                    num_trades = %s,
                    win_rate = %s,
                    sharpe_ratio = %s,
                    max_drawdown = %s,
                    avg_trade_duration = %s,
                    global_return = %s,
                    equity_curve = %s,
                    trades_details = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND graph_name = %s
                RETURNING id
            """
            cursor.execute(update_query, (
                symbol_val,
                initial_capital,
                final_capital,
                first_date,
                last_date,
                df_duration,
                total_pnl,
                total_fees,
                total_funding_cost,
                num_trades,
                win_rate,
                sharpe_ratio,
                max_drawdown,
                avg_trade_duration,
                global_return,
                equity_curve_json,
                trades_details_json,
                user_id,
                unique_graph_name
            ))
            new_id = cursor.fetchone()[0]
        else:
            insert_query = """
                INSERT INTO analyzer_results (
                    user_id, graph_name, symbol, initial_capital, final_capital, first_date, last_date,
                    df_duration, total_pnl, total_fees, total_funding_cost, num_trades, win_rate,
                    sharpe_ratio, max_drawdown, avg_trade_duration, global_return, equity_curve,
                    trades_details, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
            """
            cursor.execute(insert_query, (
                user_id,
                unique_graph_name,
                symbol_val,
                initial_capital,
                final_capital,
                first_date,
                last_date,
                df_duration,
                total_pnl,
                total_fees,
                total_funding_cost,
                num_trades,
                win_rate,
                sharpe_ratio,
                max_drawdown,
                avg_trade_duration,
                global_return,
                equity_curve_json,
                trades_details_json
            ))
            new_id = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        conn.close()
        return new_id

    @staticmethod
    def get_all_by_user(user_id, limit=10):
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT id, graph_name, updated_at 
            FROM analyzer_results 
            WHERE user_id = %s 
            ORDER BY updated_at DESC LIMIT %s
        """
        cursor.execute(query, (user_id, limit))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{'id': r[0], 'graph_name': r[1], 'updated_at': r[2]} for r in results]

    @staticmethod
    def load(user_id, analyzer_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT graph_name, symbol, initial_capital, final_capital, first_date, last_date, df_duration,
                   total_pnl, total_fees, total_funding_cost, num_trades, win_rate, sharpe_ratio,
                   max_drawdown, avg_trade_duration, global_return, equity_curve, trades_details
            FROM analyzer_results 
            WHERE user_id = %s AND id = %s
        """
        cursor.execute(query, (user_id, analyzer_id))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result:
            # Convert timedelta fields to strings if necessary.
            df_duration = result[6]
            if isinstance(df_duration, datetime.timedelta):
                df_duration = str(df_duration)
            avg_trade_duration = result[14]
            if isinstance(avg_trade_duration, datetime.timedelta):
                avg_trade_duration = str(avg_trade_duration)
            # Clean up the graph_name by removing the _bt_ suffix if present
            graph_name = result[0]
            if '_bt_' in graph_name:
                graph_name = graph_name.split('_bt_')[0]
            
            return {
                'graph_name': graph_name,
                'symbol': result[1],
                'Initial Capital': result[2],
                'Final Capital': result[3],
                'First Date': result[4],
                'Last Date': result[5],
                'DF Duration': df_duration,
                'Total PnL': result[7],
                'Total Fees': result[8],
                'Total Funding Cost': result[9],
                'Number of Trades': result[10],
                'Win Rate (%)': result[11],
                'Sharpe Ratio': result[12],
                'Max Drawdown (%)': result[13],
                'Average Trade Duration': avg_trade_duration,
                'Global Return (%)': result[15],
                'Equity Curve': result[16] if isinstance(result[16], list) else json.loads(result[16]),
                'Trades Details': result[17] if isinstance(result[17], list) else json.loads(result[17])
            }
        return None
    @staticmethod
    def delete(user_id, analyzer_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "DELETE FROM analyzer_results WHERE user_id = %s AND id = %s"
        cursor.execute(query, (user_id, analyzer_id))
        conn.commit()
        cursor.close()
        conn.close()

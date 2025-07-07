from ..utils.database import get_db_connection
import json

class BacktestResult:
    @staticmethod
    def save(user_id, graph_name, backtest_data, orders,
             precision, min_move, symbol, timeframe,
             start_date, end_date, graph):
        """
        Persist a back-test; **graph** is the raw Blockly / VPL json string.
        """
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO backtest_results (
              user_id, graph_name, backtest_data, orders,
              precision, min_move, symbol, timeframe,
              start_date, end_date, graph,
              created_at, updated_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                      CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            """,
            (
                user_id, graph_name,
                json.dumps(backtest_data),
                json.dumps(orders),
                precision, min_move, symbol, timeframe,
                start_date, end_date,
                json.dumps(graph) if not isinstance(graph, str) else graph,
            ),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close();
        conn.close()
        return new_id

    @staticmethod
    def load_by_id(record_id):
        conn = get_db_connection()
        cur  = conn.cursor()

        cur.execute(
            """
            SELECT graph_name, backtest_data, orders,
                   precision,  min_move, symbol,
                   timeframe,  start_date, end_date,
                   analyzer_result_id,
                   COALESCE(graph, 'null')  -- ← guarantees a JSON-parsable value
              FROM backtest_results
             WHERE id = %s
            """,
            (record_id,),
        )
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            return None

        (graph_name, bt_json, ord_json, prec, mm, sym, tf,
         sd, ed, res_id, graph_val) = row

        # ---------- safe conversions ----------
        bt_data = bt_json if isinstance(bt_json, list) else json.loads(bt_json)
        orders  = ord_json if isinstance(ord_json, (list, dict)) else json.loads(ord_json)

        graph_obj = (
            graph_val if isinstance(graph_val, (dict, list))
            else None if graph_val in ('null', None)
            else json.loads(graph_val)
        )

        return {
            "graph_name"        : graph_name,
            "backtest_data"     : bt_data,
            "orders"            : orders,
            "precision"         : prec,
            "min_move"          : mm,
            "symbol"            : sym,
            "timeframe"         : tf,
            "start_date"        : sd,
            "end_date"          : ed,
            "analyzer_result_id": res_id,
            "graph"             : graph_obj,   # ← may be None
        }

    @staticmethod
    def get_all_by_user(user_id, limit=10):
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT id, graph_name, orders, symbol, timeframe, start_date, end_date, updated_at, analyzer_result_id
            FROM backtest_results 
            WHERE user_id = %s 
            ORDER BY updated_at DESC LIMIT %s
        """
        cursor.execute(query, (user_id, limit))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        records = []
        for r in results:
            # Convert orders if needed; if null, set to None.
            orders = r[2] if isinstance(r[2], (list, dict)) else json.loads(r[2]) if r[2] is not None else None
            records.append({
                'id': r[0],
                'graph_name': r[1],
                'orders': orders,
                'symbol': r[3],
                'timeframe': r[4],
                'start_date': r[5],
                'end_date': r[6],
                'updated_at': r[7],
                'analyzer_result_id': r[8]
            })
        return records

    @staticmethod
    def update_analyzer_result_id(record_id, analyzer_result_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "UPDATE backtest_results SET analyzer_result_id = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        cursor.execute(query, (analyzer_result_id, record_id))
        conn.commit()
        cursor.close()
        conn.close()

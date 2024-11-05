# app/models/graph_model.py
from ..utils.database import get_db_connection
import json

class Graph:
    @staticmethod
    def save_or_update(user_id, graph_name, graph_data, start_date, end_date, symbol):
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT id FROM user_graphs WHERE user_id = %s AND name = %s"
        cursor.execute(query, (user_id, graph_name))
        existing_graph = cursor.fetchone()

        if existing_graph:
            # Update existing graph
            update_query = """
                UPDATE user_graphs
                SET 
                    graph_data = %s,
                    symbol = %s,
                    start_date = %s,
                    end_date = %s,
                    modified_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND name = %s
            """
            cursor.execute(update_query, (
                graph_data,
                symbol,
                start_date,
                end_date,
                user_id,
                graph_name
            ))
        else:
            # Insert new graph
            insert_query = """
                INSERT INTO user_graphs (
                    user_id, 
                    name, 
                    graph_data, 
                    symbol, 
                    start_date, 
                    end_date, 
                    created_at, 
                    modified_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            cursor.execute(insert_query, (
                user_id,
                graph_name,
                graph_data,
                symbol,
                start_date,
                end_date
            ))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def get_all_by_user(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT id, name, modified_at FROM user_graphs WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        graphs = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{'id': graph[0], 'name': graph[1], 'modified_at': graph[2]} for graph in graphs]

    @staticmethod
    def load(user_id, graph_name):
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT graph_data, start_date, end_date, symbol FROM user_graphs WHERE user_id = %s AND name = %s"
        cursor.execute(query, (user_id, graph_name))
        graph = cursor.fetchone()
        cursor.close()
        conn.close()
        return graph if graph else None

    @staticmethod
    def delete(user_id, graph_name):
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if graph exists before attempting to delete
        query = "SELECT id FROM user_graphs WHERE user_id = %s AND name = %s"
        cursor.execute(query, (user_id, graph_name))
        graph = cursor.fetchone()

        if graph:
            # Delete the graph if it exists
            delete_query = "DELETE FROM user_graphs WHERE user_id = %s AND name = %s"
            cursor.execute(delete_query, (user_id, graph_name))
            conn.commit()
            result = True
        else:
            result = False

        cursor.close()
        conn.close()
        return result
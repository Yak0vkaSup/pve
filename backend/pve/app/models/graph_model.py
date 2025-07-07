# app/models/graph_model.py
from ..utils.database import get_db_connection
import json
from datetime import datetime, timedelta

class Graph:
    @staticmethod
    def save_or_update(user_id, graph_name, graph_data, start_date, end_date, symbol, timeframe):
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
                    updated_at = CURRENT_TIMESTAMP,
                    timeframe = %s
                WHERE user_id = %s AND name = %s
            """
            cursor.execute(update_query, (
                graph_data,
                symbol,
                start_date,
                end_date,
                timeframe,
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
                    timeframe,
                    created_at, 
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            cursor.execute(insert_query, (
                user_id,
                graph_name,
                graph_data,
                symbol,
                start_date,
                end_date,
                timeframe,
            ))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def get_all_by_user(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT id, name, updated_at FROM user_graphs WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        graphs = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{'id': graph[0], 'name': graph[1], 'updated_at': graph[2]} for graph in graphs]

    @staticmethod
    def load(user_id, graph_name):
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT graph_data, start_date, end_date, symbol, timeframe FROM user_graphs WHERE user_id = %s AND name = %s"
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

    @staticmethod
    def delete_by_id(user_id, graph_id):
        """
        Delete a graph by ID with ownership verification.
        Returns True if deleted successfully, False if not found or not owned.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if graph exists and is owned by the user
        query = "SELECT id FROM user_graphs WHERE id = %s AND user_id = %s"
        cursor.execute(query, (graph_id, user_id))
        graph = cursor.fetchone()

        if graph:
            # Delete the graph if it exists and is owned by user
            delete_query = "DELETE FROM user_graphs WHERE id = %s AND user_id = %s"
            cursor.execute(delete_query, (graph_id, user_id))
            conn.commit()
            result = True
        else:
            result = False

        cursor.close()
        conn.close()
        return result

    @staticmethod
    def create_empty(user_id, graph_name):
        """
        Create a new empty strategy with default settings.
        Returns the ID of the created graph or None if name already exists.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if a graph with this name already exists
        check_query = "SELECT id FROM user_graphs WHERE user_id = %s AND name = %s"
        cursor.execute(check_query, (user_id, graph_name))
        existing_graph = cursor.fetchone()

        if existing_graph:
            cursor.close()
            conn.close()
            return None  # Name already exists

        # Create empty graph data
        empty_graph_data = json.dumps({
            "last_node_id": 0,
            "last_link_id": 0,
            "nodes": [],
            "links": [],
            "groups": [],
            "config": {},
            "extra": {},
            "version": 0.4
        })

        # Default settings - dynamic dates
        now = datetime.now()
        start_date = (now - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S')
        end_date = '2026-01-01T23:59:59'
        symbol = 'BTCUSDT'
        timeframe = '1h'

        # Insert new empty graph
        insert_query = """
            INSERT INTO user_graphs (
                user_id, 
                name, 
                graph_data, 
                symbol, 
                start_date, 
                end_date, 
                timeframe,
                created_at, 
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
        """
        cursor.execute(insert_query, (
            user_id,
            graph_name,
            empty_graph_data,
            symbol,
            start_date,
            end_date,
            timeframe,
        ))
        
        new_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return new_id
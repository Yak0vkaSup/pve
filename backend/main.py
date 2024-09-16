from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
import psycopg2
import pandas as pd
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

def connect_to_db():
    conn = psycopg2.connect(
        host='localhost',
        database='postgres',
        user='postgres',
        password='postgres'
    )
    return conn




if __name__ == '__main__':
    app.run(debug=True)

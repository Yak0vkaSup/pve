# app/socketio_setup.py

from flask_socketio import SocketIO
from config import Config

socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=False,
    engineio_logger=False,
    max_http_buffer_size= 20 * 1024 * 1024,  # 100 MB
    ping_timeout=2500,   # Increase from 20 seconds to 60 seconds
    ping_interval=2500  # You might also experiment with this value
)

def init_socketio(app):
    socketio.init_app(app)
    from .websocket import socket_handlers  # Import handlers after initializing socketio

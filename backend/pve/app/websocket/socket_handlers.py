# app/websocket/socket_handlers.py

from flask_socketio import join_room, leave_room, disconnect, emit
from ..utils.token_utils import verify_user_token
from flask import request, current_app
from ..socketio_setup import socketio
import logging
import threading
@socketio.on('connect')
def handle_connect():
    user_id = request.args.get('user_id')
    user_token = request.args.get('token')

    if not user_token or not user_id:
        current_app.logger.warning(f'No user[{user_id}] data received. Disconnecting client.')
        return disconnect()

    if not verify_user_token(user_id, user_token):
        current_app.logger.warning(f'Invalid user[{user_id}] token. Disconnecting client.')
        return disconnect()

    join_room(user_id)
    current_app.logger.info(f'Client connected: User ID {user_id}')

@socketio.on('disconnect')
def handle_disconnect():
    current_app.logger.info('Client disconnected')

@socketio.on('update_chart')
def update_chart():
    current_app.logger.info('Chart updated')

thread_local = threading.local()
class LogCaptureHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            user_id = getattr(thread_local, 'user_id', None)
            if user_id:
                socketio.emit('log_message', {'message': msg}, to=user_id)
        except Exception:
            self.handleError(record)
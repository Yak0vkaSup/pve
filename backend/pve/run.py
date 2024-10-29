# run.py
from app import create_app
from app.socketio_setup import socketio
from config import DevelopmentConfig

app = create_app(config_class=DevelopmentConfig)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)

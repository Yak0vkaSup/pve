# app/routes/__init__.py
from .auth_routes import auth_bp
from .backtest_routes import backtest_bp
from .bot_routes import bot_bp
from .user_routes import user_bp
from .graph_routes import graph_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(graph_bp)
    app.register_blueprint(backtest_bp)
    app.register_blueprint(bot_bp)
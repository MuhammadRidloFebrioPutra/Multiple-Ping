from flask import Flask
from config import Config
from app.database import init_db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize database
    init_db(app)
    
    # Import and register blueprints
    from app.routes.ping_routes import ping_bp
    from app.routes.whatsapp_routes import whatsapp_bp
    app.register_blueprint(ping_bp, url_prefix='/api')
    app.register_blueprint(whatsapp_bp, url_prefix='/api')
    
    return app

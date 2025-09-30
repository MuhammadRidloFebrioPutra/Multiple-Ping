from flask import Flask
from config import Config
from flask_cors import CORS
from app.database import init_db

def create_app(config_class=Config):
    app = Flask(__name__)
    CORS(app) 
    app.config.from_object(config_class)
    
    # Initialize database
    init_db(app)
    
    # Import and register blueprints
    from app.routes.ping_routes import ping_bp
    app.register_blueprint(ping_bp, url_prefix='/api')
    
    return app

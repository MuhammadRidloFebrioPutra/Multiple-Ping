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
    
    # Import and register blueprints using absolute imports
    from app.routes.ping_basic_routes import ping_basic_bp
    from app.routes.ping_service_routes import ping_service_bp
    from app.routes.ping_timeout_routes import ping_timeout_bp
    from app.routes.ping_analytics_routes import ping_analytics_bp
    # from app.routes.whatsapp_routes import whatsapp_bp  # DISABLED - Using Watzap only
    from app.routes.watzap_routes import watzap_bp
    
    # Register all blueprints
    app.register_blueprint(ping_basic_bp, url_prefix='/api/monitoring')
    app.register_blueprint(ping_service_bp, url_prefix='/api/monitoring')
    app.register_blueprint(ping_timeout_bp, url_prefix='/api/monitoring')
    app.register_blueprint(ping_analytics_bp, url_prefix='/api/monitoring')
    # app.register_blueprint(whatsapp_bp, url_prefix='/api/monitoring')  # DISABLED - Using Watzap only
    app.register_blueprint(watzap_bp, url_prefix='/api/monitoring')
    
    return app

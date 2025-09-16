"""
Database initialization and configuration
"""
import pymysql
from flask_sqlalchemy import SQLAlchemy

# Install PyMySQL as MySQLdb
# This is needed for compatibility with SQLAlchemy
pymysql.install_as_MySQLdb()

# Initialize SQLAlchemy instance
db = SQLAlchemy()

def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully")
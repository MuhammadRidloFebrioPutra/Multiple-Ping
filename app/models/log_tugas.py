from app.database import db
from datetime import datetime

class LogTugas(db.Model):
    __tablename__ = 'log_tugas'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    nama_tugas = db.Column(db.String(255), nullable=False)
    catatan = db.Column(db.Text)
    catatan_petugas = db.Column(db.Text)
    user_id = db.Column(db.BigInteger, nullable=False)  # Foreign key to users table
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<LogTugas {self.id} - {self.nama_tugas}>'
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            'id': self.id,
            'nama_tugas': self.nama_tugas,
            'catatan': self.catatan,
            'catatan_petugas': self.catatan_petugas,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<User {self.id} - {self.name}>'
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

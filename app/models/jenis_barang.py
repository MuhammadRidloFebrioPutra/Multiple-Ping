from app.database import db
from datetime import datetime

class JenisBarang(db.Model):
    __tablename__ = 'jenis_barangs'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    nama = db.Column(db.String(255), nullable=False)
    kode = db.Column(db.String(50))
    ping = db.Column(db.Integer, default=1)  # 1 = can ping, 0 = cannot ping
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<JenisBarang {self.id} - {self.nama} (ping: {self.ping})>'
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            'id': self.id,
            'nama': self.nama,
            'kode': self.kode,
            'ping': self.ping,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

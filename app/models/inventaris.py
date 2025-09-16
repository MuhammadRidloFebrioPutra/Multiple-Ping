from app.database import db
from datetime import datetime

class Inventaris(db.Model):
    __tablename__ = 'inventaris'
    
    id = db.Column(db.BigInteger, primary_key=True)
    ip = db.Column(db.String(255), nullable=False, index=True)
    hostname = db.Column(db.String(255))
    spesifikasi = db.Column(db.Text)
    asal_rak = db.Column(db.Integer)
    serial_number = db.Column(db.String(255), unique=True)
    product_number = db.Column(db.String(255))
    who_fixes = db.Column(db.BigInteger)  # Foreign key to users table
    barang_id = db.Column(db.BigInteger)  # Foreign key to barangs table
    jenis_barang_id = db.Column(db.BigInteger, nullable=False)  # Foreign key to jenis_barangs table
    os = db.Column(db.String(255))
    user = db.Column(db.String(255))
    merk = db.Column(db.String(255))
    id_lokasi = db.Column(db.BigInteger, nullable=False, index=True)  # Foreign key to lokasi_barangs table
    kondisi = db.Column(db.Enum('baik', 'maintenance', 'hilang'), nullable=False, default='baik', index=True)
    tenggat_maintenance = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Inventaris {self.ip} - {self.hostname}>'
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            'id': self.id,
            'ip': self.ip,
            'hostname': self.hostname,
            'spesifikasi': self.spesifikasi,
            'asal_rak': self.asal_rak,
            'serial_number': self.serial_number,
            'product_number': self.product_number,
            'who_fixes': self.who_fixes,
            'barang_id': self.barang_id,
            'jenis_barang_id': self.jenis_barang_id,
            'os': self.os,
            'user': self.user,
            'merk': self.merk,
            'id_lokasi': self.id_lokasi,
            'kondisi': self.kondisi,
            'tenggat_maintenance': self.tenggat_maintenance.isoformat() if self.tenggat_maintenance else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
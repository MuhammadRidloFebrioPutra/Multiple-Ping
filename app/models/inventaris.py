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
    transaksi_id = db.Column(db.BigInteger)  # Foreign key to transaksis table
    jenis_barang_id = db.Column(db.BigInteger, nullable=False)  # Foreign key to jenis_barangs table
    penanggung_jawab = db.Column(db.BigInteger)  # Foreign key to users table
    os = db.Column(db.String(255))
    penerima = db.Column(db.String(255))
    merk = db.Column(db.String(255))
    id_lokasi = db.Column(db.BigInteger, nullable=False, index=True)  # Foreign key to lokasi_barangs table
    kondisi = db.Column(db.String(50), nullable=False, default='baik', index=True)
    tenggat_maintenance = db.Column(db.Date)
    photo_path = db.Column(db.String(255))
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
            'transaksi_id': self.transaksi_id,
            'jenis_barang_id': self.jenis_barang_id,
            'penanggung_jawab': self.penanggung_jawab,
            'os': self.os,
            'penerima': self.penerima,
            'merk': self.merk,
            'id_lokasi': self.id_lokasi,
            'kondisi': self.kondisi,
            'tenggat_maintenance': self.tenggat_maintenance.isoformat() if self.tenggat_maintenance else None,
            'photo_path': self.photo_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
from app.database import db
from datetime import datetime

class Instidens(db.Model):
    __tablename__ = 'insidens'  # Fixed typo: insidens not instidens
    
    # Existing columns in database - DO NOT ADD NEW COLUMNS
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    deskripsi = db.Column(db.Text, nullable=False)
    tanggal = db.Column(db.DateTime, nullable=False, default=datetime.now)
    lokasi = db.Column(db.String(255))
    latitude = db.Column(db.String(255))
    longitude = db.Column(db.String(255))
    foto = db.Column(db.String(255))
    status = db.Column(db.String(50), nullable=False, default='new')
    bagian_perusahaan = db.Column(db.String(255), default='subreg_jawa')
    keterangan_bagian = db.Column(db.Text)
    ditugaskan_kepada = db.Column(db.BigInteger)
    catatan_petugas = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<Instidens {self.id} - {self.lokasi} ({self.status})>'
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            'id': self.id,
            'deskripsi': self.deskripsi,
            'tanggal': self.tanggal.isoformat() if self.tanggal else None,
            'lokasi': self.lokasi,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'foto': self.foto,
            'status': self.status,
            'bagian_perusahaan': self.bagian_perusahaan,
            'keterangan_bagian': self.keterangan_bagian,
            'ditugaskan_kepada': self.ditugaskan_kepada,
            'catatan_petugas': self.catatan_petugas,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

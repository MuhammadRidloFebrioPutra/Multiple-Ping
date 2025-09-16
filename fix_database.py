"""
Quick fix script untuk masalah database connection
Jalankan script ini jika mendapat error 'No module named MySQLdb'
"""

import sys
import os

def fix_mysql_connection():
    """Fix MySQL connection issues"""
    
    print("🔧 Memperbaiki konfigurasi database...")
    
    try:
        # Install PyMySQL sebagai MySQLdb
        import pymysql
        pymysql.install_as_MySQLdb()
        print("✓ PyMySQL berhasil diinstall sebagai MySQLdb")
        
        # Test import SQLAlchemy
        from sqlalchemy import create_engine
        print("✓ SQLAlchemy berhasil diimport")
        
        # Load konfigurasi
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from config import Config
        
        print(f"✓ Database URI: {Config.SQLALCHEMY_DATABASE_URI}")
        
        # Test database connection
        try:
            engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
            with engine.connect() as conn:
                result = conn.execute("SELECT 1").fetchone()
                print("✓ Database connection berhasil!")
                return True
                
        except Exception as db_error:
            print(f"✗ Database connection gagal: {db_error}")
            print("\n📋 Checklist troubleshooting:")
            print("1. Pastikan MySQL/MariaDB server berjalan")
            print("2. Periksa username/password di file .env")
            print("3. Pastikan database 'kaido_kit' sudah dibuat")
            print("4. Periksa host dan port database")
            return False
            
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("\n📦 Install dependencies:")
        print("pip install PyMySQL Flask-SQLAlchemy")
        return False
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Database Connection Fix Tool")
    print("=" * 40)
    
    success = fix_mysql_connection()
    
    if success:
        print("\n🎉 Semua test berhasil! Anda dapat menjalankan aplikasi:")
        print("python run.py")
    else:
        print("\n❌ Masih ada masalah. Periksa error di atas dan perbaiki konfigurasi.")
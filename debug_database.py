"""
Debug script untuk mengecek data inventaris di database
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    import pymysql
    pymysql.install_as_MySQLdb()
    print("✅ PyMySQL loaded successfully")
    
    from config import Config
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    
    def check_database_directly():
        """Check database directly with raw SQL"""
        print("\n🔍 Checking database directly...")
        
        config = Config()
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
        
        with engine.connect() as conn:
            # Check total records in inventaris table
            result = conn.execute(text("SELECT COUNT(*) as total FROM inventaris")).fetchone()
            print(f"Total records in inventaris table: {result[0]}")
            
            # Check all records
            result = conn.execute(text("""
                SELECT id, ip, hostname, kondisi 
                FROM inventaris 
                ORDER BY id
            """)).fetchall()
            
            print(f"\n📋 All records in database:")
            for row in result:
                print(f"  ID: {row[0]}, IP: {row[1]}, Hostname: {row[2]}, Kondisi: {row[3]}")
            
            # Check filtered records (excluding 'hilang')
            result = conn.execute(text("""
                SELECT id, ip, hostname, kondisi 
                FROM inventaris 
                WHERE kondisi != 'hilang'
                AND ip IS NOT NULL 
                AND ip != ''
                ORDER BY id
            """)).fetchall()
            
            print(f"\n✅ Active devices (kondisi != 'hilang'):")
            for row in result:
                print(f"  ID: {row[0]}, IP: {row[1]}, Hostname: {row[2]}, Kondisi: {row[3]}")
            
            return len(result)
    
    def check_with_sqlalchemy_model():
        """Check using SQLAlchemy model"""
        print("\n🔍 Checking with SQLAlchemy model...")
        
        try:
            from app.models.inventaris import Inventaris
            from app.database import db
            from sqlalchemy.orm import sessionmaker
            
            config = Config()
            engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
            Session = sessionmaker(bind=engine)
            session = Session()
            
            # Get all devices
            all_devices = session.query(Inventaris).all()
            print(f"Total devices from model: {len(all_devices)}")
            
            # Get active devices (same filter as ping service)
            active_devices = session.query(Inventaris).filter(
                Inventaris.kondisi != 'hilang',
                Inventaris.ip.isnot(None),
                Inventaris.ip != ''
            ).all()
            
            print(f"\n📋 Active devices from model:")
            for device in active_devices:
                print(f"  ID: {device.id}, IP: {device.ip}, Hostname: {device.hostname}, Kondisi: {device.kondisi}")
            
            session.close()
            return len(active_devices)
            
        except Exception as e:
            print(f"❌ Error with SQLAlchemy model: {e}")
            return 0
    
    def check_ping_service_query():
        """Check what ping service actually gets"""
        print("\n🔍 Checking ping service query...")
        
        try:
            config = Config()
            
            if config.USE_MULTI_PING:
                from app.utils.multi_ping_service import MultiPingService
                service = MultiPingService(config)
                print("Using Multi-Ping Service (Optimized)")
                
                # Check for duplicate prevention features
                print(f"Duplicate prevention enabled: {hasattr(service, '_ping_in_progress')}")
                print(f"Minimum ping interval: {getattr(service, '_min_ping_interval', 'Not set')}s")
            else:
                from app.utils.ping_service import PingMonitoringService
                service = PingMonitoringService(config)
                print("Using Single-Ping Service")
            
            devices = service.database_monitor.get_devices_from_database()
            print(f"Devices returned by ping service: {len(devices)}")
            
            print(f"\n📋 Devices from ping service:")
            for device in devices:
                print(f"  ID: {device.id}, IP: {device.ip}, Hostname: {device.hostname}, Kondisi: {device.kondisi}")
            
            return len(devices)
            
        except Exception as e:
            print(f"❌ Error with ping service: {e}")
            return 0
    
    def main():
        print("🔍 Database Debug Tool")
        print("=" * 50)
        
        config = Config()
        print(f"Database URI: {config.SQLALCHEMY_DATABASE_URI}")
        print(f"Multi-ping enabled: {config.USE_MULTI_PING}")
        
        try:
            # Check database directly
            direct_count = check_database_directly()
            
            # Check with SQLAlchemy model
            model_count = check_with_sqlalchemy_model()
            
            # Check ping service
            service_count = check_ping_service_query()
            
            print(f"\n📊 Summary:")
            print(f"  Direct SQL query: {direct_count} active devices")
            print(f"  SQLAlchemy model: {model_count} active devices")
            print(f"  Ping service query: {service_count} active devices")
            
            if direct_count > 0 and service_count == 0:
                print(f"\n⚠️  Issue detected: Database has devices but ping service can't find them")
                print(f"Possible causes:")
                print(f"1. SQLAlchemy model mapping issue")
                print(f"2. Database session/connection issue")
                print(f"3. Query filter too restrictive")
            elif service_count > 0:
                print(f"\n✅ Ping service should be pinging {service_count} devices")
                if service_count == 1:
                    print(f"💡 Only 1 device found - check if other devices have kondisi='hilang'")
            
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            print(f"\nTroubleshooting:")
            print(f"1. Make sure MySQL server is running")
            print(f"2. Check database credentials in .env file")
            print(f"3. Verify database 'kaido_kit' exists")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Install missing packages: pip install PyMySQL Flask-SQLAlchemy")

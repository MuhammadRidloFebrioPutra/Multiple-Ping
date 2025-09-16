"""
Simple debug script untuk mengecek inventaris database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    print("🔍 Database Inventaris Debug")
    print("=" * 40)
    
    try:
        import pymysql
        pymysql.install_as_MySQLdb()
        print("✅ PyMySQL loaded")
        
        from config import Config
        from sqlalchemy import create_engine, text
        
        config = Config()
        print(f"Database: {config.DB_DATABASE}")
        
        # Connect to database
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
        
        with engine.connect() as conn:
            # Check all records
            print("\n📋 All inventaris records:")
            result = conn.execute(text("""
                SELECT id, ip, hostname, kondisi 
                FROM inventaris 
                ORDER BY id
            """)).fetchall()
            
            for row in result:
                print(f"  ID:{row[0]}, IP:{row[1]}, Host:{row[2]}, Kondisi:{row[3]}")
            
            print(f"\nTotal records: {len(result)}")
            
            # Check active devices only
            print("\n✅ Active devices (kondisi != 'hilang'):")
            active_result = conn.execute(text("""
                SELECT id, ip, hostname, kondisi 
                FROM inventaris 
                WHERE kondisi != 'hilang' 
                AND ip IS NOT NULL 
                AND ip != ''
                ORDER BY id
            """)).fetchall()
            
            for row in active_result:
                print(f"  ID:{row[0]}, IP:{row[1]}, Host:{row[2]}, Kondisi:{row[3]}")
            
            print(f"\nActive devices: {len(active_result)}")
            
            if len(active_result) > 1:
                print(f"\n💡 Database has {len(active_result)} active devices")
                print(f"   But CSV only shows 1 device being pinged")
                print(f"   This suggests an issue with the ping service query")
            elif len(active_result) == 1:
                print(f"\n✅ Only 1 active device found - this matches CSV results")
            else:
                print(f"\n⚠️  No active devices found in database")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nSolutions:")
        print("1. Install: pip install PyMySQL sqlalchemy")
        print("2. Check database connection")
        print("3. Verify .env configuration")

if __name__ == "__main__":
    main()
import time
import hashlib
import logging
from datetime import datetime
from typing import Dict
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.models.inventaris import Inventaris
from app.models.jenis_barang import JenisBarang

logger = logging.getLogger(__name__)

class DatabaseMonitor:
    """
    Class untuk monitoring perubahan database dan mengelola device cache
    """
    
    def __init__(self, config):
        self.config = config
        
        # Setup database connection dengan thread-safe session
        self.engine = create_engine(
            config.SQLALCHEMY_DATABASE_URI,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False
        )
        self.Session = sessionmaker(bind=self.engine)
        
        # Database monitoring configuration
        self.device_cache = {}  # Cache untuk device list
        self.last_device_check = time.time()
        self.device_check_interval = getattr(config, 'DEVICE_CHECK_INTERVAL', 30)  # Check setiap 30 detik
        self.database_change_count = 0
    
    def get_current_device_signature(self) -> str:
        """
        Generate signature untuk current device list di database
        Join dengan jenis_barangs untuk filter berdasarkan ping = 1
        """
        session = self.Session()
        try:
            # Join dengan jenis_barangs dan filter hanya yang bisa di-ping
            devices = session.query(Inventaris).join(
                JenisBarang, Inventaris.jenis_barang_id == JenisBarang.id
            ).filter(
                Inventaris.kondisi != 'hilang',
                Inventaris.ip.isnot(None),
                Inventaris.ip != '',
                JenisBarang.ping == 1  # Filter: hanya yang bisa di-ping
            ).order_by(Inventaris.id).all()
            
            # Create signature dari device list
            device_data = []
            for device in devices:
                device_data.append(f"{device.id}:{device.ip}:{device.hostname}:{device.kondisi}")
            
            signature = hashlib.md5("|".join(device_data).encode()).hexdigest()
            return signature
            
        except Exception as e:
            logger.error(f"Error generating device signature: {e}")
            return ""
        finally:
            session.close()
    
    def check_database_changes(self) -> bool:
        """
        Check apakah ada perubahan di database sejak last check
        Returns True jika ada perubahan
        """
        current_time = time.time()
        
        # Skip jika belum waktunya check
        if current_time - self.last_device_check < self.device_check_interval:
            return False
            
        try:
            current_signature = self.get_current_device_signature()
            last_signature = self.device_cache.get('signature', '')
            
            self.last_device_check = current_time
            
            if current_signature != last_signature:
                logger.info("Database changes detected!")
                logger.info(f"Old signature: {last_signature[:16]}...")
                logger.info(f"New signature: {current_signature[:16]}...")
                
                # Update cache dengan signature baru
                self.device_cache['signature'] = current_signature
                self.database_change_count += 1
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking database changes: {e}")
            return False
    
    def reload_device_list(self) -> int:
        """
        Reload device list dari database
        Join dengan jenis_barangs untuk filter berdasarkan ping = 1
        Returns jumlah devices yang ditemukan
        """
        session = self.Session()
        try:
            # Join dengan jenis_barangs dan filter hanya yang bisa di-ping
            devices = session.query(Inventaris).join(
                JenisBarang, Inventaris.jenis_barang_id == JenisBarang.id
            ).filter(
                Inventaris.kondisi != 'hilang',
                Inventaris.ip.isnot(None),
                Inventaris.ip != '',
                JenisBarang.ping == 1  # Filter: hanya yang bisa di-ping
            ).all()
            
            # Update device cache dengan device list baru
            device_dict = {}
            for device in devices:
                device_dict[device.id] = {
                    'id': device.id,
                    'ip': device.ip,
                    'hostname': device.hostname,
                    'merk': device.merk,
                    'os': device.os,
                    'kondisi': device.kondisi,
                    'id_lokasi': device.id_lokasi
                }
            
            old_count = len(self.device_cache.get('devices', {}))
            self.device_cache['devices'] = device_dict
            new_count = len(device_dict)
            
            logger.info(f"Device list reloaded: {old_count} -> {new_count} devices (ping enabled only)")
            
            # Log specific changes
            if old_count != new_count:
                if new_count > old_count:
                    logger.info(f"Added {new_count - old_count} new pingable devices")
                else:
                    logger.info(f"Removed {old_count - new_count} devices from ping list")
            
            return new_count
            
        except Exception as e:
            logger.error(f"Error reloading device list: {e}")
            return 0
        finally:
            session.close()
    
    def get_device_count(self) -> int:
        """
        Get total number of active devices (ping enabled only)
        """
        session = self.Session()
        try:
            count = session.query(Inventaris).join(
                JenisBarang, Inventaris.jenis_barang_id == JenisBarang.id
            ).filter(
                Inventaris.kondisi != 'hilang',
                Inventaris.ip.isnot(None),
                Inventaris.ip != '',
                JenisBarang.ping == 1  # Filter: hanya yang bisa di-ping
            ).count()
            return count
        except Exception as e:
            logger.error(f"Error getting device count: {e}")
            return 0
        finally:
            session.close()
    
    def get_devices_from_database(self):
        """
        Get all active devices from database (ping enabled only)
        """
        session = self.Session()
        try:
            devices = session.query(Inventaris).join(
                JenisBarang, Inventaris.jenis_barang_id == JenisBarang.id
            ).filter(
                Inventaris.kondisi != 'hilang',
                Inventaris.ip.isnot(None),
                Inventaris.ip != '',
                JenisBarang.ping == 1  # Filter: hanya yang bisa di-ping
            ).all()
            return devices
        except Exception as e:
            logger.error(f"Error fetching devices from database: {e}")
            return []
        finally:
            session.close()
    
    def get_monitoring_status(self) -> Dict:
        """
        Get status of database monitoring
        """
        try:
            current_device_count = len(self.device_cache.get('devices', {}))
            
            return {
                'monitoring_enabled': True,
                'check_interval_seconds': self.device_check_interval,
                'last_check_timestamp': datetime.fromtimestamp(self.last_device_check).isoformat(),
                'change_detection_count': self.database_change_count,
                'cached_device_count': current_device_count,
                'current_signature': self.device_cache.get('signature', '')[:16] + '...' if self.device_cache.get('signature') else 'Not set'
            }
        except Exception as e:
            logger.error(f"Error getting monitoring status: {e}")
            return {
                'monitoring_enabled': False,
                'error': str(e)
            }
    
    def force_device_reload(self) -> Dict:
        """
        Force reload device list dari database
        Returns status info
        """
        try:
            old_count = len(self.device_cache.get('devices', {}))
            new_count = self.reload_device_list()
            
            # Update signature
            self.device_cache['signature'] = self.get_current_device_signature()
            self.database_change_count += 1
            
            return {
                'success': True,
                'old_device_count': old_count,
                'new_device_count': new_count,
                'devices_added': max(0, new_count - old_count),
                'devices_removed': max(0, old_count - new_count),
                'reload_timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error forcing device reload: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def initialize_cache(self):
        """
        Initialize device cache pada startup
        """
        self.reload_device_list()
        self.device_cache['signature'] = self.get_current_device_signature()
        logger.info("Database monitor initialized with device cache")
    
    def __del__(self):
        """
        Cleanup resources
        """
        # Engine akan otomatis cleanup connections
        if hasattr(self, 'engine'):
            self.engine.dispose()
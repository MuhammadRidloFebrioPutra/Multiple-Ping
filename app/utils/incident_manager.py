"""
Incident Manager - Menangani pembuatan insiden untuk device yang timeout berkepanjangan
"""
import os
import csv
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.database import db
from app.models.instidens import Instidens
from app.models.inventaris import Inventaris

logger = logging.getLogger(__name__)

class IncidentManager:
    """
    Class untuk mengelola pembuatan insiden otomatis untuk device yang timeout
    berkepanjangan (lebih dari 1 jam setelah alert)
    """
    
    def __init__(self, config, app=None):
        self.config = config
        self.app = app  # Store Flask app instance for context
        self.timeout_dir = getattr(config, 'CSV_OUTPUT_DIR', 'ping_results')
        self.alerted_list_csv = os.path.join(self.timeout_dir, 'whatsapp_alerted_list.csv')
        self.incident_tracking_csv = os.path.join(self.timeout_dir, 'incident_tracking.csv')
        
        # Configuration
        self.incident_threshold_minutes = getattr(config, 'INCIDENT_THRESHOLD_MINUTES', 60)  # 1 hour
        self.check_interval_minutes = getattr(config, 'INCIDENT_CHECK_INTERVAL_MINUTES', 10)  # Check every 10 minutes
        
        # Ensure directory exists
        os.makedirs(self.timeout_dir, exist_ok=True)
        
        # CSV headers for incident tracking
        self.incident_headers = [
            'ip_address', 'hostname', 'device_id', 'alert_time', 
            'incident_id', 'incident_created_at', 'device_type'
        ]
        
        # Initialize tracking CSV
        self._initialize_incident_tracking_csv()
        
        logger.info(f"IncidentManager initialized - Threshold: {self.incident_threshold_minutes} minutes")
    
    def _initialize_incident_tracking_csv(self):
        """Initialize incident tracking CSV file with headers if not exists"""
        if not os.path.exists(self.incident_tracking_csv):
            try:
                with open(self.incident_tracking_csv, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self.incident_headers)
                    writer.writeheader()
                logger.info(f"Created new incident tracking CSV: {self.incident_tracking_csv}")
            except Exception as e:
                logger.error(f"Error creating incident tracking CSV: {e}")
    
    def _read_alerted_devices(self) -> Dict[str, Dict]:
        """Read devices from whatsapp_alerted_list.csv with their alert times"""
        alerted_devices = {}
        
        if not os.path.exists(self.alerted_list_csv):
            return alerted_devices
        
        try:
            with open(self.alerted_list_csv, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    ip_address = row.get('ip_address')
                    if ip_address:
                        alerted_devices[ip_address] = row
            
            logger.debug(f"Read {len(alerted_devices)} alerted devices from CSV")
            return alerted_devices
            
        except Exception as e:
            logger.error(f"Error reading alerted devices CSV: {e}")
            return {}
    
    def _read_incident_tracking(self) -> Dict[str, Dict]:
        """Read existing incident tracking data"""
        incident_data = {}
        
        if not os.path.exists(self.incident_tracking_csv):
            return incident_data
        
        try:
            with open(self.incident_tracking_csv, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    ip_address = row.get('ip_address')
                    if ip_address:
                        incident_data[ip_address] = row
            
            logger.debug(f"Read {len(incident_data)} incident tracking entries")
            return incident_data
            
        except Exception as e:
            logger.error(f"Error reading incident tracking CSV: {e}")
            return {}
    
    def _write_incident_tracking(self, incident_data: Dict[str, Dict]):
        """Write incident tracking data to CSV"""
        try:
            with open(self.incident_tracking_csv, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.incident_headers)
                writer.writeheader()
                
                for row_data in incident_data.values():
                    writer.writerow(row_data)
                    
            logger.debug(f"Written {len(incident_data)} incident tracking entries to CSV")
            
        except Exception as e:
            logger.error(f"Error writing incident tracking CSV: {e}")
    
    def _get_device_info(self, ip_address: str, hostname: str = None, device_id: str = None) -> Dict:
        """Get device information from database"""
        try:
            if not self.app:
                logger.warning("No Flask app available - using minimal device info")
                return {
                    'device_id': device_id if device_id else None,
                    'hostname': hostname or 'Unknown',
                    'ip_address': ip_address,
                    'merk': 'Unknown',
                    'os': 'Unknown',
                    'jenis_barang_id': None
                }
            
            # Use Flask app context for database queries
            with self.app.app_context():
                # Try to find device by IP
                device = Inventaris.query.filter_by(ip=ip_address).first()
                
                if device:
                    return {
                        'device_id': device.id,
                        'hostname': device.hostname or hostname or 'Unknown',
                        'ip_address': device.ip,
                        'merk': device.merk or 'Unknown',
                        'os': device.os or 'Unknown',
                        'jenis_barang_id': device.jenis_barang_id
                    }
                else:
                    # Device not found in database, use provided info
                    return {
                        'device_id': device_id if device_id else None,
                        'hostname': hostname or 'Unknown',
                        'ip_address': ip_address,
                        'merk': 'Unknown',
                        'os': 'Unknown',
                        'jenis_barang_id': None
                    }
                
        except Exception as e:
            logger.error(f"Error getting device info for {ip_address}: {e}")
            return {
                'device_id': device_id if device_id else None,
                'hostname': hostname or 'Unknown',
                'ip_address': ip_address,
                'merk': 'Unknown',
                'os': 'Unknown',
                'jenis_barang_id': None
            }
    
    def _create_incident(self, device_info: Dict, alert_time: datetime) -> Optional[int]:
        """Create incident in database - using only existing table columns"""
        try:
            if not self.app:
                logger.error("Cannot create incident - No Flask app available")
                return None
            
            # Use Flask app context for database operations
            with self.app.app_context():
                # Determine device type description
                device_type = f"{device_info.get('merk', 'Unknown')} {device_info.get('os', 'Device')}"
                hostname = device_info.get('hostname', 'Unknown')
                ip_address = device_info.get('ip_address', 'Unknown')
                device_id = device_info.get('device_id')
                
                # Create detailed incident description (store all device info here)
                deskripsi = f"Device {device_type} ({hostname}) non aktif selama lebih dari 1 jam.\n\n"
                deskripsi += f"Detail Device:\n"
                deskripsi += f"- Hostname: {hostname}\n"
                deskripsi += f"- IP Address: {ip_address}\n"
                if device_id:
                    deskripsi += f"- Device ID: {device_id}\n"
                deskripsi += f"- Merk: {device_info.get('merk', 'Unknown')}\n"
                deskripsi += f"- OS: {device_info.get('os', 'Unknown')}\n\n"
                deskripsi += f"Timeline:\n"
                deskripsi += f"- First Alert: {alert_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                deskripsi += f"- Incident Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                # Create detailed keterangan_bagian (additional tracking info)
                keterangan_bagian = None
                
                # Create new incident - ONLY using existing columns
                incident = Instidens(
                    deskripsi=deskripsi,
                    tanggal=datetime.now(),
                    lokasi=hostname,
                    latitude=None,
                    longitude=None,
                    foto=None,
                    status='new',
                    bagian_perusahaan='subreg_jawa',
                    keterangan_bagian=keterangan_bagian,
                    ditugaskan_kepada=None,
                    catatan_petugas=None
                )
                
                db.session.add(incident)
                db.session.commit()
                
                logger.info(f"✅ Incident created successfully for {hostname} ({ip_address}) - ID: {incident.id}")
                print(f"   📋 Incident ID {incident.id} dibuat untuk {hostname} ({ip_address})")
                
                return incident.id
            
        except Exception as e:
            logger.error(f"❌ Error creating incident for {device_info.get('ip_address')}: {e}")
            if self.app:
                with self.app.app_context():
                    db.session.rollback()
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return None
    
    def check_and_create_incidents(self, timeout_data: Dict[str, Dict]) -> List[int]:
        """
        Check alerted devices and create incidents for those that have been 
        down for more than the threshold time
        
        Args:
            timeout_data: Dictionary of current timeout data from timeout_tracker
            
        Returns:
            List of created incident IDs
        """
        try:
            created_incidents = []
            current_time = datetime.now()
            
            # Read alerted devices and existing incidents
            incident_tracking = self._read_incident_tracking()
            
            # Check each device in timeout_data
            for ip_address, device_data in timeout_data.items():
                # Skip if incident already created for this device
                if ip_address in incident_tracking:
                    logger.debug(f"Incident already exists for {ip_address}, skipping")
                    continue
                
                # Get first timeout time
                first_timeout = device_data.get('first_timeout')
                if not first_timeout:
                    continue
                
                try:
                    first_timeout_dt = datetime.fromisoformat(first_timeout)
                except:
                    logger.warning(f"Invalid first_timeout format for {ip_address}: {first_timeout}")
                    continue
                
                # Calculate time difference
                time_diff = current_time - first_timeout_dt
                time_diff_minutes = time_diff.total_seconds() / 60
                
                # Check if threshold reached
                if time_diff_minutes >= self.incident_threshold_minutes:
                    logger.warning(f"🚨 Device {ip_address} has been down for {time_diff_minutes:.1f} minutes (threshold: {self.incident_threshold_minutes})")
                    print(f"\n🚨 INCIDENT THRESHOLD REACHED!")
                    print(f"   Device: {device_data.get('hostname', 'Unknown')} ({ip_address})")
                    print(f"   Down time: {time_diff_minutes:.1f} minutes (threshold: {self.incident_threshold_minutes} minutes)")
                    print(f"   Creating incident...")
                    
                    # Get full device info
                    device_info = self._get_device_info(
                        ip_address, 
                        device_data.get('hostname'),
                        device_data.get('device_id')
                    )
                    
                    # Create incident
                    incident_id = self._create_incident(device_info, first_timeout_dt)
                    
                    if incident_id:
                        # Track incident creation
                        incident_tracking[ip_address] = {
                            'ip_address': ip_address,
                            'hostname': device_info.get('hostname', 'Unknown'),
                            'device_id': device_info.get('device_id', ''),
                            'alert_time': first_timeout_dt.isoformat(),
                            'incident_id': str(incident_id),
                            'incident_created_at': current_time.isoformat(),
                            'device_type': f"{device_info.get('merk', 'Unknown')} {device_info.get('os', 'Device')}"
                        }
                        
                        created_incidents.append(incident_id)
                        print(f"   ✅ Incident ID {incident_id} berhasil dibuat!")
                    else:
                        print(f"   ❌ Gagal membuat incident!")
            
            # Update incident tracking CSV
            if created_incidents:
                self._write_incident_tracking(incident_tracking)
                logger.info(f"Created {len(created_incidents)} new incidents")
            
            return created_incidents
            
        except Exception as e:
            logger.error(f"Error in check_and_create_incidents: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return []
    
    def cleanup_resolved_incidents(self, recovered_ips: List[str]):
        """
        Remove incident tracking for devices that have recovered
        
        Args:
            recovered_ips: List of IP addresses that have recovered
        """
        try:
            incident_tracking = self._read_incident_tracking()
            updated = False
            
            for ip_address in recovered_ips:
                if ip_address in incident_tracking:
                    incident_id = incident_tracking[ip_address].get('incident_id')
                    hostname = incident_tracking[ip_address].get('hostname', ip_address)
                    
                    logger.info(f"Device {hostname} ({ip_address}) recovered - Removing from incident tracking")
                    print(f"   🔄 Device {hostname} pulih - Incident ID {incident_id} dapat ditutup")
                    
                    del incident_tracking[ip_address]
                    updated = True
            
            if updated:
                self._write_incident_tracking(incident_tracking)
                
        except Exception as e:
            logger.error(f"Error cleaning up resolved incidents: {e}")
    
    def get_incident_summary(self) -> Dict:
        """Get summary of incident tracking"""
        try:
            incident_tracking = self._read_incident_tracking()
            
            return {
                'total_incidents_created': len(incident_tracking),
                'threshold_minutes': self.incident_threshold_minutes,
                'check_interval_minutes': self.check_interval_minutes,
                'tracking_csv_path': self.incident_tracking_csv,
                'incidents': list(incident_tracking.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting incident summary: {e}")
            return {}

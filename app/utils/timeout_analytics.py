import os
import csv
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

class TimeoutAnalytics:
    """
    Class untuk mengelola analytics timeout CCTV dalam format time-series
    """
    
    def __init__(self, config):
        self.config = config
        self.analytics_dir = getattr(config, 'CSV_OUTPUT_DIR', 'ping_results')
        self.analytics_filename_prefix = 'timeout_analytics'
        
        # Ensure directory exists
        os.makedirs(self.analytics_dir, exist_ok=True)
        
        # CSV headers for timeout analytics - Only 2 columns
        self.analytics_headers = [
            'timestamp', 'total_timeout_devices'
        ]
        
        logger.info(f"TimeoutAnalytics initialized - Directory: {self.analytics_dir}")
    
    def get_analytics_csv_path(self, date_str: str = None) -> str:
        """Get analytics CSV file path for specific date or today"""
        if date_str is None:
            date_str = datetime.now().strftime('%Y%m%d')
        
        filename = f"{self.analytics_filename_prefix}_{date_str}.csv"
        return os.path.join(self.analytics_dir, filename)
    
    def _initialize_analytics_csv(self, csv_path: str):
        """Initialize analytics CSV file with headers if not exists"""
        if not os.path.exists(csv_path):
            try:
                with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self.analytics_headers)
                    writer.writeheader()
                logger.info(f"Created new timeout analytics CSV: {os.path.basename(csv_path)}")
            except Exception as e:
                logger.error(f"Error creating analytics CSV: {e}")
    
    def record_timeout_snapshot(self, timeout_data: Dict[str, Dict], 
                               previous_timeout_ips: set = None) -> bool:
        """
        Record current timeout snapshot to analytics CSV
        Args:
            timeout_data: Current timeout data from TimeoutTracker
            previous_timeout_ips: Set of IPs that were timing out in previous snapshot
        """
        try:
            current_time = datetime.now()
            csv_path = self.get_analytics_csv_path()
            
            # Initialize CSV if needed
            self._initialize_analytics_csv(csv_path)
            
            # Calculate analytics metrics
            current_timeout_ips = set(timeout_data.keys())
            total_timeout_devices = len(current_timeout_ips)
            
            # Only 2 fields in analytics record
            analytics_record = {
                'timestamp': current_time.isoformat(),
                'total_timeout_devices': total_timeout_devices
            }
            
            # Append to CSV
            with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.analytics_headers)
                writer.writerow(analytics_record) 
            
            logger.debug(f"Recorded timeout analytics: {total_timeout_devices} devices")
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording timeout snapshot: {e}")
            return False

    def get_analytics_data(self, hours: int = 24, date_str: str = None) -> List[Dict]:
        """ 
        Get timeout analytics data for time-series chart
        Args:
            hours: Number of hours to retrieve (default: 24)
            date_str: Specific date in YYYYMMDD format (default: today)
        """
        try:
            if date_str is None:
                date_str = datetime.now().strftime('%Y%m%d')
            
            csv_path = self.get_analytics_csv_path(date_str)
            
            if not os.path.exists(csv_path):
                logger.warning(f"Analytics CSV file not found: {os.path.basename(csv_path)}")
                return []
            
            # Calculate time range
            now = datetime.now()
            start_time = now - timedelta(hours=hours)
            
            analytics_data = []
            
            with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    try:
                        record_time = datetime.fromisoformat(row['timestamp'])
                        
                        # Filter by time range
                        if record_time >= start_time:
                            # Convert numeric fields - only 1 numeric field now
                            row['total_timeout_devices'] = int(row['total_timeout_devices'])
                            analytics_data.append(row)
                            
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Skipping invalid analytics record: {e}")
                        continue
            
            logger.info(f"Retrieved {len(analytics_data)} analytics records from last {hours} hours")
            return analytics_data
            
        except Exception as e:
            logger.error(f"Error getting analytics data: {e}")
            return []

    def get_multi_day_analytics(self, days: int = 7) -> List[Dict]:
        """
        Get analytics data spanning multiple days
        Args:
            days: Number of days to retrieve (default: 7)
        """
        try:
            all_data = []
            current_date = datetime.now()
            
            for i in range(days):
                date_to_check = current_date - timedelta(days=i)
                date_str = date_to_check.strftime('%Y%m%d')
                
                day_data = self.get_analytics_data(hours=24, date_str=date_str)
                all_data.extend(day_data)
            
            # Sort by timestamp
            all_data.sort(key=lambda x: x['timestamp'])
            
            logger.info(f"Retrieved {len(all_data)} analytics records from last {days} days")
            return all_data
            
        except Exception as e:
            logger.error(f"Error getting multi-day analytics: {e}")
            return []
    
    def get_analytics_summary(self, hours: int = 24) -> Dict:
        """
        Get summary statistics for analytics data
        """
        try:
            data = self.get_analytics_data(hours=hours)
            
            if not data:
                return {
                    'total_records': 0,
                    'time_range_hours': hours,
                    'avg_timeout_devices': 0,
                    'peak_timeout_devices': 0,
                    'avg_critical_devices': 0,
                    'peak_critical_devices': 0
                }
            
            # Calculate summary statistics
            timeout_counts = [record['total_timeout_devices'] for record in data]
            critical_counts = [record['critical_devices_count'] for record in data]
            
            summary = {
                'total_records': len(data),
                'time_range_hours': hours,
                'avg_timeout_devices': round(sum(timeout_counts) / len(timeout_counts), 2),
                'peak_timeout_devices': max(timeout_counts),
                'avg_critical_devices': round(sum(critical_counts) / len(critical_counts), 2),
                'peak_critical_devices': max(critical_counts),
                'first_record': data[0]['timestamp'],
                'last_record': data[-1]['timestamp']
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            return {}
    
    def cleanup_old_analytics_files(self, keep_days: int = 30):
        """Clean up analytics files older than specified days"""
        try:
            if not os.path.exists(self.analytics_dir):
                return
            
            current_time = datetime.now()
            deleted_files = 0
            
            for filename in os.listdir(self.analytics_dir):
                if filename.startswith(self.analytics_filename_prefix) and filename.endswith('.csv'):
                    file_path = os.path.join(self.analytics_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    # Calculate age in days
                    age_days = (current_time - file_time).days
                    
                    if age_days > keep_days:
                        try:
                            os.remove(file_path)
                            deleted_files += 1
                            logger.info(f"Deleted old analytics file: {filename} (age: {age_days} days)")
                        except Exception as e:
                            logger.error(f"Error deleting analytics file {filename}: {e}")
            
            if deleted_files > 0:
                logger.info(f"Cleaned up {deleted_files} old analytics files")
                
        except Exception as e:
            logger.error(f"Error during analytics cleanup: {e}")
            
            for filename in os.listdir(self.analytics_dir):
                if filename.startswith(self.analytics_filename_prefix) and filename.endswith('.csv'):
                    file_path = os.path.join(self.analytics_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    # Calculate age in days
                    age_days = (current_time - file_time).days
                    
                    if age_days > keep_days:
                        try:
                            os.remove(file_path)
                            deleted_files += 1
                            logger.info(f"Deleted old analytics file: {filename} (age: {age_days} days)")
                        except Exception as e:
                            logger.error(f"Error deleting analytics file {filename}: {e}")
            
            if deleted_files > 0:
                logger.info(f"Cleaned up {deleted_files} old analytics files")
                
        except Exception as e:
            logger.error(f"Error during analytics cleanup: {e}")
            logger.info(f"Deleted old analytics file: {filename} (age: {age_days} days)")
            if deleted_files > 0:
                logger.info(f"Cleaned up {deleted_files} old analytics files")
                
        except Exception as e:
            logger.error(f"Error during analytics cleanup: {e}")

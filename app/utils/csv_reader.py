import csv
import os
import glob
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from config import Config
import json

class CSVReader:
    def __init__(self, config: Config):
        self.config = config
        self.csv_dir = config.CSV_OUTPUT_DIR
    
    def get_available_csv_files(self) -> List[str]:
        """
        Get list of all available CSV files
        """
        pattern = os.path.join(self.csv_dir, "ping_results_*.csv")
        files = glob.glob(pattern)
        # Sort by modification time (newest first)
        files.sort(key=os.path.getmtime, reverse=True)
        return files
    
    def read_csv_file(self, filename: str) -> List[Dict]:
        """
        Read a single CSV file and return list of dictionaries
        """
        filepath = os.path.join(self.csv_dir, filename)
        results = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Convert string values to appropriate types
                    row['device_id'] = int(row['device_id']) if row['device_id'] else None
                    row['ping_success'] = row['ping_success'].lower() == 'true'
                    row['response_time_ms'] = float(row['response_time_ms']) if row['response_time_ms'] else None
                    results.append(row)
            return results
        except Exception as e:
            print(f"Error reading CSV file {filename}: {e}")
            return []
    
    def get_latest_ping_results(self, limit: int = 100) -> List[Dict]:
        """
        Get the latest ping results across all CSV files
        """
        all_results = []
        files = self.get_available_csv_files()
        
        for file in files:
            filename = os.path.basename(file)
            results = self.read_csv_file(filename)
            all_results.extend(results)
            
            # Stop if we have enough results
            if len(all_results) >= limit:
                break
        
        # Sort by timestamp (newest first) and limit
        all_results.sort(key=lambda x: x['timestamp'], reverse=True)
        return all_results[:limit]
    
    def get_ping_results_by_device(self, device_id: int, hours: int = 24) -> List[Dict]:
        """
        Get ping results for a specific device within the last X hours
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff_time.isoformat()
        
        device_results = []
        files = self.get_available_csv_files()
        
        for file in files:
            filename = os.path.basename(file)
            results = self.read_csv_file(filename)
            
            for result in results:
                if (result['device_id'] == device_id and 
                    result['timestamp'] >= cutoff_str):
                    device_results.append(result)
        
        # Sort by timestamp (newest first)
        device_results.sort(key=lambda x: x['timestamp'], reverse=True)
        return device_results
    
    def get_ping_statistics(self, device_id: Optional[int] = None, hours: int = 24) -> Dict:
        """
        Get ping statistics for all devices or a specific device
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff_time.isoformat()
        
        all_results = []
        files = self.get_available_csv_files()
        
        for file in files:
            filename = os.path.basename(file)
            results = self.read_csv_file(filename)
            
            filtered_results = [
                r for r in results 
                if r['timestamp'] >= cutoff_str and 
                   (device_id is None or r['device_id'] == device_id)
            ]
            all_results.extend(filtered_results)
        
        if not all_results:
            return {
                'total_pings': 0,
                'successful_pings': 0,
                'failed_pings': 0,
                'success_rate': 0.0,
                'average_response_time_ms': None,
                'min_response_time_ms': None,
                'max_response_time_ms': None
            }
        
        successful_pings = [r for r in all_results if r['ping_success']]
        response_times = [r['response_time_ms'] for r in successful_pings if r['response_time_ms'] is not None]
        
        return {
            'total_pings': len(all_results),
            'successful_pings': len(successful_pings),
            'failed_pings': len(all_results) - len(successful_pings),
            'success_rate': round((len(successful_pings) / len(all_results)) * 100, 2),
            'average_response_time_ms': round(sum(response_times) / len(response_times), 2) if response_times else None,
            'min_response_time_ms': min(response_times) if response_times else None,
            'max_response_time_ms': max(response_times) if response_times else None
        }
    
    def get_device_status_summary(self) -> Dict:
        """
        Get current status summary for all devices
        """
        latest_results = {}
        files = self.get_available_csv_files()
        
        # Get the most recent ping result for each device
        for file in files:
            filename = os.path.basename(file)
            results = self.read_csv_file(filename)
            
            for result in results:
                device_id = result['device_id']
                if (device_id not in latest_results or 
                    result['timestamp'] > latest_results[device_id]['timestamp']):
                    latest_results[device_id] = result
        
        # Group by status
        online_devices = []
        offline_devices = []
        
        for device_id, result in latest_results.items():
            device_info = {
                'device_id': device_id,
                'ip_address': result['ip_address'],
                'hostname': result['hostname'],
                'last_seen': result['timestamp'],
                'response_time_ms': result['response_time_ms']
            }
            
            if result['ping_success']:
                online_devices.append(device_info)
            else:
                device_info['error_message'] = result['error_message']
                offline_devices.append(device_info)
        
        return {
            'total_devices': len(latest_results),
            'online_devices': len(online_devices),
            'offline_devices': len(offline_devices),
            'devices': {
                'online': online_devices,
                'offline': offline_devices
            }
        }
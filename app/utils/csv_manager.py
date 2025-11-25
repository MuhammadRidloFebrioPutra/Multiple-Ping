import os
import csv
import logging
import tempfile
import shutil
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

class CSVManager:
    """
    Class untuk menangani operasi CSV file
    """
    
    def __init__(self, config):
        self.config = config
        self.csv_dir = getattr(config, 'CSV_OUTPUT_DIR', 'ping_results')
        
        # Ensure CSV output directory exists
        os.makedirs(self.csv_dir, exist_ok=True)
        
        # CSV headers
        self.csv_headers = [
            'timestamp', 'device_id', 'ip_address', 'hostname', 
            'ping_success', 'response_time_ms', 'latency_ms', 'error_message',
            'merk', 'os', 'kondisi', 'id_lokasi'
        ]
    
    # def write_ping_results_to_csv(self, results: List[Dict], active_ips: List[str] = None):
    #     """
    #     Write/Update ping results to CSV file.
    #     Behavior:
    #     - Update (replace) row per IP yang masih aktif
    #     - Hapus IP yang sudah tidak ada lagi (misal kondisi berubah jadi 'hilang') jika active_ips disediakan
    #     Param:
    #       results: list hasil ping cycle sekarang
    #       active_ips: daftar IP aktif dari database (optional). Jika diberikan, CSV akan dipruning sesuai daftar ini.
    #     """
    #     timestamp = datetime.now()
    #     csv_filename = f"ping_results_{timestamp.strftime('%Y%m%d')}.csv"
    #     csv_path = os.path.join(self.csv_dir, csv_filename)
        
    #     try:
    #         # Read existing data if file exists
    #         existing_data = {}
    #         if os.path.exists(csv_path):
    #             with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
    #                 reader = csv.DictReader(csvfile)
    #                 for row in reader:
    #                     # Use ip_address as key for existing data
    #                     existing_data[row['ip_address']] = row
            
    #         # Jika active_ips diberikan, prune entries yang tidak lagi aktif
    #         if active_ips is not None:
    #             active_set = set(active_ips)
    #             removed = [ip for ip in existing_data.keys() if ip not in active_set]
    #             if removed:
    #                 for ip in removed:
    #                     existing_data.pop(ip, None)
    #                 logger.info(f"Pruned {len(removed)} stale IP(s) from CSV: {removed}")

    #         # Update existing data with new results
    #         for result in results:
    #             ip_address = result['ip_address']
    #             # Remove processing_time_ms from CSV output
    #             csv_row = {k: v for k, v in result.items() if k in self.csv_headers}
    #             existing_data[ip_address] = csv_row
            
    #         # Write all data back to CSV (overwrites the file)
    #         with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
    #             writer = csv.DictWriter(csvfile, fieldnames=self.csv_headers)
    #             writer.writeheader()
                
    #             # Write all data (updated and existing)
    #             for ip_address, row_data in existing_data.items():
    #                 writer.writerow(row_data)
                    
    #         logger.info(f"Successfully updated {len(results)} ping results in {csv_filename}")
    #         logger.info(f"Total active unique IPs in CSV: {len(existing_data)}")
            
    #     except Exception as e:
    #         logger.error(f"Error writing to CSV file: {e}")
    
    def get_latest_ping_results_from_csv(self, limit: int = None) -> List[Dict]:
        """
        Get latest ping results from today's CSV file
        Returns one entry per IP (the latest update)
        """
        timestamp = datetime.now()
        csv_filename = f"ping_results_{timestamp.strftime('%Y%m%d')}.csv"
        csv_path = os.path.join(self.csv_dir, csv_filename)
        
        results = []
        
        if not os.path.exists(csv_path):
            logger.warning(f"CSV file {csv_filename} not found")
            return results
        
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                # Since we now update in place, each IP appears only once
                # So we can just read all rows
                for row in reader:
                    results.append(dict(row))
                    
            # Apply limit if specified
            if limit:
                results = results[:limit]
                
            logger.info(f"Retrieved {len(results)} unique ping results from {csv_filename}")
            return results
            
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            return []
    
    def get_available_csv_files(self) -> List[Dict]:
        """
        Get list of available CSV files with metadata
        """
        csv_files = []
        
        try:
            if not os.path.exists(self.csv_dir):
                return csv_files
                
            for filename in os.listdir(self.csv_dir):
                if filename.startswith('ping_results_') and filename.endswith('.csv'):
                    file_path = os.path.join(self.csv_dir, filename)
                    file_stats = os.stat(file_path)
                    
                    # Extract date from filename
                    date_str = filename.replace('ping_results_', '').replace('.csv', '')
                    try:
                        file_date = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
                    except ValueError:
                        file_date = 'Unknown'
                    
                    # Count lines in CSV (excluding header)
                    line_count = 0
                    try:
                        with open(file_path, 'r') as f:
                            line_count = sum(1 for line in f) - 1  # Exclude header
                    except Exception:
                        line_count = 0
                    
                    csv_files.append({
                        'filename': filename,
                        'date': file_date,
                        'size_bytes': file_stats.st_size,
                        'device_count': line_count,
                        'last_modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                    })
                    
            # Sort by date descending (newest first)
            csv_files.sort(key=lambda x: x['filename'], reverse=True)
            return csv_files
            
        except Exception as e:
            logger.error(f"Error getting CSV files: {e}")
            return []
    
    def get_csv_file_path(self, date_str: str = None) -> str:
        """
        Get CSV file path for specific date or today
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y%m%d')
        
        csv_filename = f"ping_results_{date_str}.csv"
        return os.path.join(self.csv_dir, csv_filename)
    
    def cleanup_old_csv_files(self, keep_days: int = 30):
        """
        Clean up CSV files older than specified days
        """
        try:
            if not os.path.exists(self.csv_dir):
                return
            
            current_time = datetime.now()
            deleted_files = 0
            
            for filename in os.listdir(self.csv_dir):
                if filename.startswith('ping_results_') and filename.endswith('.csv'):
                    file_path = os.path.join(self.csv_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    # Calculate age in days
                    age_days = (current_time - file_time).days
                    
                    if age_days > keep_days:
                        try:
                            os.remove(file_path)
                            deleted_files += 1
                            logger.info(f"Deleted old CSV file: {filename} (age: {age_days} days)")
                        except Exception as e:
                            logger.error(f"Error deleting file {filename}: {e}")
            
            if deleted_files > 0:
                logger.info(f"Cleaned up {deleted_files} old CSV files")
                
        except Exception as e:
            logger.error(f"Error during CSV cleanup: {e}")
    
    def get_csv_statistics(self) -> Dict:
        """
        Get statistics about CSV files
        """
        try:
            csv_files = self.get_available_csv_files()
            
            total_size = sum(f['size_bytes'] for f in csv_files)
            total_devices = sum(f['device_count'] for f in csv_files)
            
            return {
                'total_files': len(csv_files),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'total_devices_recorded': total_devices,
                'oldest_file': csv_files[-1]['date'] if csv_files else None,
                'newest_file': csv_files[0]['date'] if csv_files else None
            }
            
        except Exception as e:
            logger.error(f"Error getting CSV statistics: {e}")
            return {}
        


    def write_ping_results_to_csv(self, results: List[Dict], active_ips: List[str] = None):
        timestamp = datetime.now()
        csv_filename = f"ping_results_{timestamp.strftime('%Y%m%d')}.csv"
        csv_path = os.path.join(self.csv_dir, csv_filename)

        # Buat temporary file di folder yang sama (penting!)
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=f"{csv_filename}.",
            suffix=".tmp",
            dir=self.csv_dir
        )

        try:
            # Pastikan file langsung kosong dan siap tulis
            os.close(tmp_fd)  # kita tidak pakai fd, kita buka ulang dengan encoding

            # Baca data lama (kalau file asli ada dan tidak rusak)
            existing_data = {}
            if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
                try:
                    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if row.get('ip_address'):
                                existing_data[row['ip_address']] = row
                except Exception as e:
                    logger.warning(f"File CSV lama rusak, mulai dari nol: {e}")

            # Prune kalau perlu
            if active_ips is not None:
                for ip in list(existing_data.keys()):
                    if ip not in active_ips:
                        existing_data.pop(ip, None)

            # Update dengan hasil terbaru
            for result in results:
                ip = result['ip_address']
                row = {k: v for k, v in result.items() if k in self.csv_headers}
                existing_data[ip] = row

            # Tulis ke temporary file
            with open(tmp_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.csv_headers)
                writer.writeheader()
                for row in existing_data.values():
                    writer.writerow(row)
                
                # PAKSA tulis ke disk sebelum rename
                f.flush()
                os.fsync(f.fileno())

            # Atomic replace → ini yang bikin tidak pernah truncated
            shutil.move(tmp_path, csv_path)
            
            logger.info(f"CSV updated safely → {csv_filename} ({len(existing_data)} devices)")

        except Exception as e:
            logger.error(f"GAGAL tulis CSV: {e}")
            # Bersihkan file temporary kalau gagal
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except:
                pass
            raise
        finally:
            # Kalau entah kenapa tmp_path masih ada (super rare)
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except:
                pass
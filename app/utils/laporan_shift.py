"""
Laporan Shift Service - Mengirim laporan aktivitas user ke WhatsApp secara berkala
Jadwal pengiriman: 08:00 (pagi), 16:00 (sore), 00:00 (malam)
"""
import os
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.models.log_tugas import LogTugas, User

logger = logging.getLogger(__name__)

class LaporanShiftService:
    """
    Service untuk mengirim laporan shift ke WhatsApp secara otomatis
    """
    
    def __init__(self, config, watzap_service=None, app=None):
        self.config = config
        self.watzap_service = watzap_service
        self.app = app
        self.running = False
        self.thread = None
        
        # Jadwal pengiriman laporan (jam)
        self.report_hours = [8, 16, 0]  # 08:00, 16:00, 00:00
        
        # Setup database connection dengan thread-safe session
        self.engine = create_engine(
            config.SQLALCHEMY_DATABASE_URI,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False
        )
        self.Session = sessionmaker(bind=self.engine)
        
        # Track last report time untuk mencegah duplikasi
        self.last_report_date = {}
        for hour in self.report_hours:
            self.last_report_date[hour] = None
        
        # Configuration
        self.enabled = getattr(config, 'ENABLE_SHIFT_REPORT', True)
        self.target_group = getattr(config, 'SHIFT_REPORT_GROUP', None)
        
        logger.info(f"LaporanShiftService initialized")
        logger.info(f"Report schedule: {self.report_hours}")
        logger.info(f"Status: {'Enabled' if self.enabled else 'Disabled'}")
    
    def get_shift_name(self, hour: int) -> str:
        """Get shift name based on hour"""
        if hour == 8:
            return "Shift Pagi (00:00 - 08:00)"
        elif hour == 16:
            return "Shift Siang (08:00 - 16:00)"
        elif hour == 0:
            return "Shift Malam (16:00 - 00:00)"
        return f"Shift Jam {hour}"
    
    def get_shift_time_range(self, current_hour: int) -> tuple:
        """
        Get time range for current shift
        Returns (start_time, end_time)
        """
        now = datetime.now()
        
        if current_hour == 8:
            # Shift pagi: 00:00 - 08:00 hari ini
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
        elif current_hour == 16:
            # Shift siang: 08:00 - 16:00 hari ini
            start_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
            end_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
        elif current_hour == 0:
            # Shift malam: 16:00 kemarin - 00:00 hari ini
            yesterday = now - timedelta(days=1)
            start_time = yesterday.replace(hour=16, minute=0, second=0, microsecond=0)
            end_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Default: 8 jam sebelumnya
            end_time = now
            start_time = now - timedelta(hours=8)
        
        return start_time, end_time
    
    def get_log_tugas_data(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """
        Get log tugas data from database for the specified time range
        """
        session = self.Session()
        try:
            # Query dengan JOIN ke users table
            results = session.query(
                LogTugas.nama_tugas,
                LogTugas.catatan,
                LogTugas.catatan_petugas,
                User.name,
                LogTugas.created_at
            ).join(
                User, LogTugas.user_id == User.id
            ).filter(
                LogTugas.created_at >= start_time,
                LogTugas.created_at < end_time
            ).order_by(
                LogTugas.created_at.desc()
            ).all()
            
            # Convert to list of dictionaries
            log_data = []
            for row in results:
                log_data.append({
                    'nama_tugas': row.nama_tugas,
                    'catatan': row.catatan,
                    'catatan_petugas': row.catatan_petugas,
                    'user_name': row.name,
                    'created_at': row.created_at
                })
            
            logger.info(f"Found {len(log_data)} log tugas entries for period {start_time} to {end_time}")
            return log_data
            
        except Exception as e:
            logger.error(f"Error getting log tugas data: {e}")
            return []
        finally:
            session.close()
    
    def format_laporan_message(self, shift_name: str, start_time: datetime, end_time: datetime, log_data: List[Dict]) -> str:
        """
        Format laporan message for WhatsApp
        Group activities by nama_tugas (nama_kegiatan) instead of by user
        """
        message = f"📊 *LAPORAN {shift_name.upper()}*\n"
        message += f"{'='*40}\n\n"
        message += f"📅 *Periode:* {start_time.strftime('%d/%m/%Y %H:%M')} - {end_time.strftime('%d/%m/%Y %H:%M')}\n"
        
        if not log_data:
            message += "ℹ️ Tidak ada aktivitas yang tercatat pada shift ini.\n"
        else:
            message += f"{'='*40}\n\n"
            
            # Group by nama_tugas (nama_kegiatan)
            activity_groups = {}
            for log in log_data:
                nama_tugas = log.get('nama_tugas', 'Aktivitas Lainnya')
                if nama_tugas not in activity_groups:
                    activity_groups[nama_tugas] = []
                activity_groups[nama_tugas].append(log)
            
            # Format per activity group
            for idx, (nama_tugas, logs) in enumerate(activity_groups.items(), 1):
                message += f"*{idx}. {nama_tugas}*\n"
                
                # Show all catatan and catatan_petugas for this activity
                for log in logs:
                    if log.get('catatan'):
                        message += f"   📌 {log.get('catatan')}\n"
                    
                    if log.get('catatan_petugas'):
                        message += f"   🔧 Keterangan: {log.get('catatan_petugas')}\n"
                
                message += f"\n"
        
        message += f"{'='*40}\n"
        message += f"Laporan digenerate otomatis oleh sistematis\n"
        message += f"📅 {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n"
        
        return message
    
    def send_shift_report(self, hour: int) -> bool:
        """
        Send shift report for specific hour
        """
        try:
            if not self.watzap_service:
                logger.error("Watzap service not available")
                return False
            
            # Get shift info
            shift_name = self.get_shift_name(hour)
            start_time, end_time = self.get_shift_time_range(hour)
            
            logger.info(f"Generating {shift_name} report...")
            logger.info(f"Period: {start_time} to {end_time}")
            
            # Get log tugas data
            log_data = self.get_log_tugas_data(start_time, end_time)
            
            # Format message
            message = self.format_laporan_message(shift_name, start_time, end_time, log_data)
            
            # Send via Watzap
            if self.target_group:
                logger.info(f"Sending report to group: {self.target_group}")
                result = self.watzap_service.send_to_group(self.target_group, message)
            else:
                logger.info("No target group specified, sending as broadcast")
                result = self.watzap_service.broadcast_message(message)
            
            if result and result.get('success'):
                logger.info(f"✅ {shift_name} report sent successfully!")
                return True
            else:
                logger.error(f"❌ Failed to send {shift_name} report: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending shift report: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def should_send_report(self, current_hour: int) -> bool:
        """
        Check if report should be sent for current hour
        """
        # Check if current hour matches any report schedule
        if current_hour not in self.report_hours:
            return False
        
        # Check if report already sent today for this hour
        today_date = datetime.now().strftime('%Y-%m-%d')
        last_sent = self.last_report_date.get(current_hour)
        
        if last_sent == today_date:
            return False  # Already sent today
        
        return True
    
    def mark_report_sent(self, hour: int):
        """Mark report as sent for today"""
        today_date = datetime.now().strftime('%Y-%m-%d')
        self.last_report_date[hour] = today_date
        logger.info(f"Report for hour {hour} marked as sent for {today_date}")
    
    def monitoring_loop(self):
        """
        Main monitoring loop - check setiap menit
        """
        logger.info("📊 Laporan Shift monitoring started")
        
        while self.running:
            try:
                now = datetime.now()
                current_hour = now.hour
                current_minute = now.minute
                
                # Check hanya di menit ke-0 (awal jam)
                if current_minute == 0:
                    if self.should_send_report(current_hour):
                        logger.info(f"⏰ Report time! Hour: {current_hour}")
                        
                        # Send report
                        success = self.send_shift_report(current_hour)
                        
                        if success:
                            self.mark_report_sent(current_hour)
                        else:
                            logger.warning(f"Report sending failed for hour {current_hour}")
                
                # Sleep 60 detik sebelum check lagi
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Continue after error
    
    def start(self):
        """Start the shift report service"""
        if not self.enabled:
            logger.info("Laporan Shift service is disabled")
            return
        
        if self.running:
            logger.warning("Laporan Shift service already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        self.thread.start()
        logger.info("✅ Laporan Shift service started")
    
    def stop(self):
        """Stop the shift report service"""
        if not self.running:
            return
        
        logger.info("Stopping Laporan Shift service...")
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=5)
        
        logger.info("✅ Laporan Shift service stopped")
    
    def get_status(self) -> Dict:
        """Get service status"""
        return {
            'running': self.running,
            'enabled': self.enabled,
            'report_hours': self.report_hours,
            'target_group': self.target_group,
            'last_report_dates': self.last_report_date,
            'next_reports': self._get_next_report_times()
        }
    
    def _get_next_report_times(self) -> List[str]:
        """Get next scheduled report times"""
        now = datetime.now()
        next_reports = []
        
        for hour in sorted(self.report_hours):
            next_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            # If time already passed today, schedule for tomorrow
            if next_time <= now:
                next_time += timedelta(days=1)
            
            next_reports.append(next_time.strftime('%Y-%m-%d %H:%M'))
        
        return next_reports


# Global singleton instance
_laporan_shift_service = None

def get_laporan_shift_service(config=None, watzap_service=None, app=None):
    """
    Get singleton instance of laporan shift service
    """
    global _laporan_shift_service
    if _laporan_shift_service is None and config:
        _laporan_shift_service = LaporanShiftService(config, watzap_service, app)
    return _laporan_shift_service

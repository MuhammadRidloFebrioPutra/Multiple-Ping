# Multi-Ping Monitoring System

Sistem monitoring ping untuk perangkat inventaris yang mengambil data dari database, melakukan ping multiple devices secara concurrent, menyimpan hasil ke CSV, dan menyediakan API untuk mengakses hasil ping.

## Fitur Utama

1. **Database Integration**: Mengambil data perangkat otomatis dari tabel `inventaris`
2. **Concurrent Multi-Ping**: Ping multiple perangkat secara bersamaan untuk performa optimal
3. **Background Monitoring**: Ping semua perangkat setiap 5 detik secara otomatis
4. **High Performance**: ThreadPoolExecutor untuk handling ratusan devices
5. **CSV Storage**: Menyimpan hasil ping ke file CSV dengan rotasi harian
6. **REST API**: API lengkap untuk monitoring dan control
7. **Real-time Statistics**: Statistik performa dan status perangkat
8. **Scalable Configuration**: Atur concurrent workers sesuai kapasitas sistem
9. **🆕 Duplicate Prevention**: Kontrol otomatis untuk mencegah ping ganda
10. **🆕 Performance Optimization**: Cache dan kontrol cycle untuk efisiensi maksimal
11. **🆕 Timeout Tracking**: Sistem tracking timeout berturut-turut per device

## File CSV Output

Hasil ping disimpan dalam direktori `ping_results/` dengan format:

- **Ping Results**: `ping_results_YYYYMMDD.csv`

  - Nama file: `ping_results_YYYYMMDD.csv`
  - Format: CSV dengan header
  - Rotasi: File baru setiap hari
  - Kolom: timestamp, device_id, ip_address, hostname, ping_success, response_time_ms, error_message
  - **🆕 Optimized**: Tidak ada duplikasi entry dalam interval yang sama

- **🆕 Timeout Tracking**: `timeout_tracking.csv`
  - Nama file: `timeout_tracking.csv` (single file, updated continuously)
  - Format: CSV dengan header untuk tracking timeout berturut-turut
  - Kolom: ip_address, hostname, device_id, merk, os, kondisi, consecutive_timeouts, first_timeout, last_timeout, last_updated
  - **Behavior**:
    - IP yang timeout ditambahkan dengan consecutive_timeouts = 1
    - Timeout berturut-turut menambah counter tanpa duplikasi (satu IP satu line)
    - IP yang ping berhasil dihapus dari tracking
    - Data diurutkan berdasarkan consecutive_timeouts (tertinggi di atas)

## API Endpoints

### 1. Health Check

```
GET /api/health
```

### 2. Latest Ping Results

```
GET /api/ping/latest?limit=100
```

### 3. Device Specific Results

```
GET /api/ping/device/{device_id}?hours=24
```

### 4. Ping Statistics

```
GET /api/ping/statistics?device_id={optional}&hours=24
```

### 5. Device Status Summary

```
GET /api/ping/status
```

### 6. Service Management

```
GET  /api/ping/service/status
POST /api/ping/service/start
POST /api/ping/service/stop
```

### 7. Test Ping

```
POST /api/ping/test/{ip_address}
```

### 8. CSV Rebuild (Optimized)

```
POST /api/ping/csv/rebuild
```

### 🆕 9. Timeout Tracking Endpoints

```
GET /api/ping/timeout/summary
GET /api/ping/timeout/devices?min_consecutive=1
GET /api/ping/timeout/critical?threshold=5
GET /api/ping/timeout/report
POST /api/ping/timeout/reset
```

### 🆕 10. WhatsApp Timeout Alert Endpoints

```
GET /api/ping/timeout/whatsapp/summary
POST /api/ping/timeout/whatsapp/test?ip_address=10.2.30.184
```

## Contoh Response API

### 🆕 Timeout Summary

```json
{
  "success": true,
  "data": {
    "total_timeout_devices": 15,
    "max_consecutive_timeouts": 25,
    "average_consecutive_timeouts": 8.5,
    "devices_with_high_timeouts": 3,
    "timeout_csv_path": "ping_results/timeout_tracking.csv"
  }
}
```

### 🆕 Timeout Devices

```json
{
  "success": true,
  "data": [
    {
      "ip_address": "10.2.30.184",
      "hostname": "POCC",
      "device_id": "1",
      "merk": "Vivotek FD8377-HV",
      "os": "",
      "kondisi": "baik",
      "consecutive_timeouts": "25",
      "first_timeout": "2025-09-19T10:45:47.075895",
      "last_timeout": "2025-09-19T11:21:55.432375",
      "last_updated": "2025-09-19T11:21:55.432375"
    }
  ],
  "count": 1,
  "min_consecutive_filter": 1
}
```

### 🆕 Service Status (Enhanced with Timeout Tracking)

```json
{
  "success": true,
  "service_type": "Multi-Ping Service (Optimized + Timeout Tracking)",
  "service_running": true,
  "timeout_tracking": {
    "enabled": true,
    "csv_file": "ping_results/timeout_tracking.csv",
    "summary": {
      "total_timeout_devices": 15,
      "max_consecutive_timeouts": 25,
      "devices_with_high_timeouts": 3
    }
  }
}
```

### 🆕 WhatsApp Alert Summary

```json
{
  "success": true,
  "data": {
    "total_alerts_sent": 10,
    "devices_alerted": 7,
    "critical_timeouts_detected": 3
  }
}
```

## Konfigurasi

Konfigurasi dapat diatur melalui environment variables:

**Basic Configuration:**

- `PING_INTERVAL`: Interval ping dalam detik (default: 5)
- `CSV_OUTPUT_DIR`: Direktori output CSV (default: ping_results)
- `MAX_CSV_RECORDS`: Maksimal record per file CSV (default: 1000)

**Multi-Ping Configuration:**

- `USE_MULTI_PING`: Enable/disable multi-threading (default: true)
- `MAX_PING_WORKERS`: Jumlah concurrent ping workers (default: 20)
- `PING_TIMEOUT`: Timeout per ping dalam detik (default: 3)

**🆕 Timeout Tracking Configuration:**

- `ENABLE_TIMEOUT_TRACKING`: Enable/disable timeout tracking (default: true)
- `TIMEOUT_CRITICAL_THRESHOLD`: Consecutive timeouts untuk dianggap critical (default: 5)

**🆕 WhatsApp Timeout Alert Configuration:**

- `ENABLE_WHATSAPP_TIMEOUT_ALERTS`: Enable/disable WhatsApp alerts for timeouts (default: true)
- `WHATSAPP_TIMEOUT_THRESHOLD`: Consecutive timeouts before sending WhatsApp alert (default: 20)
- `WHATSAPP_COOLDOWN_MINUTES`: Cooldown period between alerts for same device (default: 60)

### Contoh .env dengan Timeout Tracking dan WhatsApp Alerts

```env
DB_CONNECTION=mysql+pymysql
DB_HOST=localhost
DB_PORT=3306
DB_DATABASE=kaido_kit
DB_USERNAME=root
DB_PASSWORD=

# Multi-Ping Configuration
USE_MULTI_PING=true
MAX_PING_WORKERS=20
PING_TIMEOUT=3
PING_INTERVAL=5

# Timeout Tracking
ENABLE_TIMEOUT_TRACKING=true
TIMEOUT_CRITICAL_THRESHOLD=5

# WhatsApp Timeout Alerts
ENABLE_WHATSAPP_TIMEOUT_ALERTS=true
WHATSAPP_TIMEOUT_THRESHOLD=20
WHATSAPP_COOLDOWN_MINUTES=60
```

## 🚨 WhatsApp Timeout Alert System

### Features

- **Automatic Alerts**: Mengirim WhatsApp alert otomatis ketika device mencapai 20 consecutive timeouts
- **Smart Cooldown**: Mencegah spam dengan cooldown period 60 menit per device
- **Rich Information**: Alert berisi detail lengkap device (IP, hostname, brand, etc.)
- **Recovery Tracking**: Otomatis stop alert ketika device kembali online
- **Alert History**: Track semua alert yang pernah dikirim

### Alert Message Format

```
🚨 DEVICE TIMEOUT ALERT 🚨

⚠️ CRITICAL: Device Tidak Dapat Dijangkau!

📍 Device Information:
• IP Address: 10.2.30.184
• Hostname: POCC
• Device ID: 1
• Brand/Model: Vivotek FD8377-HV
• Status: baik

⏰ Timeout Details:
• Consecutive Timeouts: 20
• First Timeout: 26-09-2025 12:26:13
• Last Check: 26-09-2025 12:54:48

🔧 Action Required:
1. Check device power and network connection
2. Verify network connectivity to 10.2.30.184
3. Physical inspection may be required
4. Contact technical support if issue persists

Alert Time: 26-09-2025 12:55:02 WIB
```

### 🆕 WhatsApp Timeout Alert Endpoints

```
GET /api/ping/timeout/whatsapp/summary    # Get WhatsApp alert summary
POST /api/ping/timeout/whatsapp/test?ip_address=10.2.30.184    # Test alert for specific IP
```

## 🔧 Monitoring dan Troubleshooting

### 🆕 Timeout Tracking Features

#### 1. Automatic Timeout Detection

- **Real-time Tracking**: Setiap ping cycle secara otomatis update timeout tracking
- **Consecutive Counter**: Menghitung timeout berturut-turut per IP address
- **Auto Cleanup**: IP yang kembali online otomatis dihapus dari tracking

#### 2. Critical Timeout Alerts

- **Threshold-based**: Konfigurasi threshold untuk timeout critical
- **Prioritized List**: Device dengan timeout terbanyak di urutan atas
- **Comprehensive Report**: Export report lengkap untuk analisis

#### 3. CSV Format Timeout Tracking

```csv
ip_address,hostname,device_id,merk,os,kondisi,consecutive_timeouts,first_timeout,last_timeout,last_updated
10.2.30.184,POCC,1,Vivotek FD8377-HV,,baik,25,2025-09-19T10:45:47.075895,2025-09-19T11:21:55.432375,2025-09-19T11:21:55.432375
```

### 🆕 Timeout Monitoring Workflow

1. **Ping Execution** → Results contain success/failure per IP
2. **Timeout Analysis** → Failed pings increment consecutive counter
3. **CSV Update** → Single line per IP, no redundancy
4. **Success Recovery** → Successful ping removes IP from tracking
5. **Critical Alerts** → API endpoints untuk monitoring critical timeouts

## Kebutuhan Sistem

- Python 3.7+
- MySQL/MariaDB server
- Network access ke perangkat yang akan di-ping
- Permissions untuk membuat file CSV di direktori output
- **🆕 Recommended**: RAM minimal 2GB untuk handling > 200 devices + timeout tracking
- **🆕 Recommended**: CPU minimal 2 cores untuk optimal threading + timeout processing

## 📊 Performance Benchmarks (Updated)

| Device Count | Recommended Config         | Expected Ping Time | Memory Usage | Timeout Tracking |
| ------------ | -------------------------- | ------------------ | ------------ | ---------------- |
| < 50         | Workers: 10, Interval: 5s  | ~3s                | ~100MB       | ~1MB             |
| 50-200       | Workers: 20, Interval: 5s  | ~5s                | ~200MB       | ~5MB             |
| 200-500      | Workers: 30, Interval: 10s | ~8s                | ~400MB       | ~10MB            |
| > 500        | Workers: 50, Interval: 15s | ~12s               | ~800MB       | ~20MB            |

**Note**: Dengan optimasi duplicate prevention dan timeout tracking, sistem dapat handle monitoring yang lebih comprehensive dengan overhead minimal.

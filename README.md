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

## Instalasi

1. **Clone repository dan masuk ke direktori**

```bash
cd "Ping"
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Setup environment variables**

```bash
copy env.example .env
```

Edit file `.env` sesuai dengan konfigurasi database Anda:

```env
DB_CONNECTION=mysql+pymysql
DB_HOST=
DB_PORT=
DB_DATABASE=
DB_USERNAME=
DB_PASSWORD=

# Multi-Ping Configuration (Example)
USE_MULTI_PING=true 
MAX_PING_WORKERS=20
PING_TIMEOUT=3
```

4. **Jalankan aplikasi**

```bash
python run.py
```

## Struktur Database

Sistem ini menggunakan tabel `inventaris` dengan struktur:

- `id`: Primary key
- `ip`: IP address perangkat (wajib)
- `hostname`: Nama host perangkat
- `kondisi`: Kondisi perangkat ('baik', 'maintenance', 'hilang')
- Dan field lainnya sesuai SQL dump

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

## Contoh Response API

### Latest Ping Results

```json
{
  "success": true,
  "data": [
    {
      "timestamp": "2025-09-16T10:30:00.123456",
      "device_id": 1,
      "ip_address": "192.168.1.11",
      "hostname": "host-inventaris-1",
      "ping_success": true,
      "response_time_ms": 1.23,
      "error_message": ""
    }
  ],
  "count": 1
}
```

### Statistics

```json
{
  "success": true,
  "statistics": {
    "total_pings": 100,
    "successful_pings": 95,
    "failed_pings": 5,
    "success_rate": 95.0,
    "average_response_time_ms": 1.45,
    "min_response_time_ms": 0.8,
    "max_response_time_ms": 3.2
  }
}
```

### Device Status Summary

```json
{
  "success": true,
  "data": {
    "total_devices": 3,
    "online_devices": 2,
    "offline_devices": 1,
    "devices": {
      "online": [
        {
          "device_id": 1,
          "ip_address": "192.168.1.11",
          "hostname": "host-inventaris-1",
          "last_seen": "2025-09-16T10:30:00.123456",
          "response_time_ms": 1.23
        }
      ],
      "offline": [
        {
          "device_id": 3,
          "ip_address": "192.168.1.13",
          "hostname": "host-inventaris-3",
          "last_seen": "2025-09-16T10:29:55.123456",
          "error_message": "No response (timeout)"
        }
      ]
    }
  }
}
```

## File CSV Output

Hasil ping disimpan dalam direktori `ping_results/` dengan format:

- Nama file: `ping_results_YYYYMMDD.csv`
- Format: CSV dengan header
- Rotasi: File baru setiap hari
- Kolom: timestamp, device_id, ip_address, hostname, ping_success, response_time_ms, error_message

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

### Optimization Tips

**Untuk Jaringan Kecil (< 50 devices):**

```env
USE_MULTI_PING=true
MAX_PING_WORKERS=10
PING_TIMEOUT=2
```

**Untuk Jaringan Menengah (50-200 devices):**

```env
USE_MULTI_PING=true
MAX_PING_WORKERS=20
PING_TIMEOUT=3
```

**Untuk Jaringan Besar (> 200 devices):**

```env
USE_MULTI_PING=true
MAX_PING_WORKERS=50
PING_TIMEOUT=5
```

## Cara Kerja Sistem

### Single-Ping Mode (USE_MULTI_PING=false)

1. **Sequential Processing**: Ping satu per satu device secara berurutan
2. **Slower**: Waktu total = jumlah device × ping timeout
3. **Lower Resource**: Menggunakan resource CPU dan network minimal

### Multi-Ping Mode (USE_MULTI_PING=true) - **Recommended**

1. **Concurrent Processing**: Ping multiple devices secara bersamaan
2. **Faster**: Waktu total ≈ ping timeout (terlepas dari jumlah device)
3. **Scalable**: Dapat handle ratusan device dengan performa optimal
4. **Efficient**: Menggunakan ThreadPoolExecutor untuk resource management

### Flow Diagram

```
Database Query → Get Active Devices → Multi-Ping Execution → CSV Storage → API Access
     ↓               ↓                        ↓                   ↓           ↓
[inventaris]    [IP addresses]         [ThreadPool]         [CSV Files]  [REST API]
 kondisi≠hilang   valid IPs only       max_workers=20       daily rotation  real-time
```

## Monitoring dan Troubleshooting

### Common Issues dan Solutions

#### 1. ModuleNotFoundError: No module named 'MySQLdb'

**Error**: `ModuleNotFoundError: No module named 'MySQLdb'`

**Solution**:

- Pastikan PyMySQL sudah terinstall dengan benar
- Pastikan konfigurasi database menggunakan `mysql+pymysql` di file `.env`
- Install ulang dependencies: `pip install PyMySQL`

#### 2. Database Connection Error

**Error**: Database connection failed

**Solutions**:

- Pastikan MySQL/MariaDB server berjalan
- Periksa kredensial database di file `.env`
- Test koneksi dengan: `python test_connection.py`
- Pastikan database `kaido_kit` sudah dibuat

#### 3. Import Errors

**Error**: `Import "flask" could not be resolved`

**Solutions**:

- Aktifkan virtual environment: `myenv\Scripts\activate`
- Install dependencies: `pip install -r requirements.txt`
- Verifikasi Python version: `python --version`

### Testing Tools

1. **Test Database Connection**:

   ```bash
   python test_connection.py
   ```

2. **Test Basic App**:
   ```bash
   python test_app.py
   ```
   Lalu akses:
   - http://localhost:5000/test
   - http://localhost:5000/test-db
   - http://localhost:5000/test-ping

### Log Monitoring

- **Log Output**: Aplikasi akan menampilkan log aktivitas ping monitoring
- **Service Status**: Gunakan endpoint `/api/ping/service/status` untuk cek status service
- **Test Ping**: Gunakan endpoint `/api/ping/test/{ip}` untuk test ping manual
- **CSV Files**: Periksa direktori `ping_results/` untuk file output

## Kebutuhan Sistem

- Python 3.7+
- MySQL/MariaDB server
- Network access ke perangkat yang akan di-ping
- Permissions untuk membuat file CSV di direktori output

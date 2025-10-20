"""
Simple test script untuk Watzap API
"""
from app.utils.watzap_service import WatzapService
from datetime import datetime

def test_connection():
    """Test koneksi"""
    print("=" * 60)
    print("Testing Watzap Connection")
    print("=" * 60)
    
    service = WatzapService()
    status = service.get_status()
    
    print(f"\n✅ Service Info:")
    print(f"   - Service: {status.get('service_name')}")
    print(f"   - API Key: {status.get('api_key')}")
    print(f"   - Default Group: {status.get('default_group')}")
    print(f"   - Status: {status.get('overall_status')}")
    
    return status

def test_send_message():
    """Test kirim pesan"""
    print("\n" + "=" * 60)
    print("Testing Send Message")
    print("=" * 60)
    
    service = WatzapService()
    
    message = f"""🧪 TEST MESSAGE

Ini adalah pesan test dari Watzap Integration.

Waktu: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} WIB

Jika Anda menerima pesan ini, berarti integrasi berhasil! ✅"""
    
    print(f"\n📤 Sending message...")
    result = service.send_message(message=message)
    
    if result['status'] == 'success':
        print("✅ Message sent successfully!")
        print(f"   Response: {result.get('data', {})}")
    else:
        print(f"❌ Failed: {result.get('message')}")
        
        # Show detailed error
        if 'data' in result:
            error_data = result['data']
            print(f"\n⚠️  Error Details:")
            print(f"   Status Code: {error_data.get('status')}")
            print(f"   Message: {error_data.get('message')}")
            print(f"   ACK: {error_data.get('ack')}")
            
            # Specific error handling
            if error_data.get('status') == '1003':
                print(f"\n💡 Solusi:")
                print(f"   1. Login ke https://watzap.id/login")
                print(f"   2. Cek status lisensi di dashboard")
                print(f"   3. Aktivasi/perpanjang lisensi")
                print(f"   4. Atau gunakan API key yang valid")
    
    return result

def test_timeout_alert():
    """Test timeout alert"""
    print("\n" + "=" * 60)
    print("Testing Timeout Alert")
    print("=" * 60)
    
    service = WatzapService()
    
    device_data = {
        'ip_address': '192.168.1.100',
        'hostname': 'Test-CCTV-01',
        'device_id': 'CCTV-TEST-001',
        'merk': 'Test Brand',
        'kondisi': 'Aktif',
        'consecutive_timeouts': 15,
        'first_timeout': '2025-10-20 10:00:00',
        'last_timeout': '2025-10-20 10:15:00'
    }
    
    print(f"\n🚨 Sending timeout alert for {device_data['hostname']}...")
    result = service.send_timeout_alert(device_data)
    
    if result['status'] == 'completed':
        print(f"✅ Alert sent! Success: {result['success_count']}/{result['total']}")
    else:
        print(f"❌ Failed: {result.get('message')}")
    
    return result

if __name__ == "__main__":
    print("\n" + "🚀" * 30)
    print("WATZAP SERVICE TEST")
    print("🚀" * 30 + "\n")
    
    try:
        # Test 1: Connection
        status = test_connection()
        
        if status.get('overall_status') != 'ready':
            print("\n⚠️  Service configuration OK, tapi akan test dengan kirim pesan nyata.")
            print("    Lanjutkan untuk test pengiriman pesan...")
        
        # Test 2: Send Message
        print("\n" + "⏸️" * 30)
        choice = input("\n📤 Test kirim pesan? (y/n): ").lower()
        if choice == 'y':
            test_send_message()
        
        # Test 3: Timeout Alert
        print("\n" + "⏸️" * 30)
        choice = input("\n🚨 Test timeout alert? (y/n): ").lower()
        if choice == 'y':
            test_timeout_alert()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted")
    except Exception as e:
        print(f"\n\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
